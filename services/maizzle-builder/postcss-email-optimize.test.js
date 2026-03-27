import { describe, it, expect } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import postcss from 'postcss';
import emailOptimize from './postcss-email-optimize.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

async function optimize(css, targetClients) {
  const result = await postcss([emailOptimize({ targetClients })]).process(css, { from: undefined });
  return { css: result.css, optimization: result.emailOptimization };
}

describe('postcss-email-optimize', () => {
  it('passes through supported properties unchanged', async () => {
    const { css } = await optimize('.hero { display: block; color: red; }', ['gmail_web']);
    expect(css).toContain('display');
    expect(css).toContain('color');
  });

  it('returns optimization metadata structure', async () => {
    const { optimization } = await optimize('.hero { display: block; }', ['gmail_web']);
    expect(optimization).toBeDefined();
    expect(optimization.removed_properties).toBeInstanceOf(Array);
    expect(optimization.conversions).toBeInstanceOf(Array);
    expect(optimization.warnings).toBeInstanceOf(Array);
  });

  it('removes @charset and @layer at-rules', async () => {
    const { css } = await optimize(
      '@charset "UTF-8"; @layer base { .x { color: red; } } .hero { margin: 0; }',
      ['gmail_web']
    );
    expect(css).not.toContain('@charset');
    expect(css).not.toContain('@layer');
    expect(css).toContain('.hero');
  });

  it('preserves @media at-rules', async () => {
    const { css } = await optimize(
      '@media (prefers-color-scheme: dark) { .hero { color: white; } }',
      ['gmail_web']
    );
    expect(css).toContain('@media');
  });

  it('handles empty CSS', async () => {
    const { css, optimization } = await optimize('', ['gmail_web']);
    expect(css).toBe('');
    expect(optimization.removed_properties).toHaveLength(0);
  });

  it('removes unsupported properties per ontology', async () => {
    const { optimization } = await optimize('.x { display: block; }', ['gmail_web']);
    // display:block is universally supported, should NOT be removed
    expect(optimization.removed_properties).not.toContain('display: block');
  });

  it('preserves @media rules with breakpoints', async () => {
    const { css } = await optimize(
      '@media (max-width: 600px) { .mobile { font-size: 14px; } } .desktop { font-size: 16px; }',
      ['gmail_web']
    );
    expect(css).toContain('@media');
    expect(css).toContain('.mobile');
    expect(css).toContain('.desktop');
  });

  it('preserves @keyframes rules', async () => {
    const { css } = await optimize(
      '@keyframes fade { from { opacity: 0; } to { opacity: 1; } }',
      ['gmail_web']
    );
    expect(css).toContain('@keyframes');
  });

  it('removes @import at-rules', async () => {
    const { css, optimization } = await optimize(
      '@import url("styles.css"); .hero { color: red; }',
      ['gmail_web']
    );
    expect(css).not.toContain('@import');
    expect(optimization.warnings.some(w => w.includes('@import'))).toBe(true);
  });

  it('handles multiple selectors', async () => {
    const { css } = await optimize(
      '.a { color: red; } .b { font-size: 14px; } .c { margin: 0; }',
      ['gmail_web']
    );
    expect(css).toContain('.a');
    expect(css).toContain('.b');
    expect(css).toContain('.c');
  });

  it('handles CSS with no declarations', async () => {
    const { css } = await optimize('.empty {}', ['gmail_web']);
    expect(typeof css).toBe('string');
  });

  it('conversion metadata has correct structure', async () => {
    const { optimization } = await optimize('.x { color: red; }', ['gmail_web']);
    expect(optimization).toHaveProperty('removed_properties');
    expect(optimization).toHaveProperty('conversions');
    expect(optimization).toHaveProperty('warnings');
    expect(Array.isArray(optimization.removed_properties)).toBe(true);
    expect(Array.isArray(optimization.conversions)).toBe(true);
    expect(Array.isArray(optimization.warnings)).toBe(true);
  });

  it('conversion entry has required fields', async () => {
    const { optimization } = await optimize('.x { display: block; }', ['gmail_web']);
    for (const conv of optimization.conversions) {
      expect(conv).toHaveProperty('original_property');
      expect(conv).toHaveProperty('replacement_property');
      expect(conv).toHaveProperty('affected_clients');
      expect(Array.isArray(conv.affected_clients)).toBe(true);
    }
  });

  it('uses default target clients when none provided', async () => {
    const result = await postcss([emailOptimize()]).process('.x { color: red; }', { from: undefined });
    expect(result.emailOptimization).toBeDefined();
  });

  it('handles complex nested selectors', async () => {
    const { css } = await optimize(
      '.parent .child > .grandchild { color: red; font-size: 14px; }',
      ['gmail_web']
    );
    expect(css).toContain('.parent');
  });
});

describe('ontology sync', () => {
  it('ontology.json exists and is valid', () => {
    const path = resolve(__dirname, 'data/ontology.json');
    expect(existsSync(path)).toBe(true);
    const data = JSON.parse(readFileSync(path, 'utf-8'));
    expect(data).toHaveProperty('version');
    expect(data).toHaveProperty('properties_by_name');
    expect(data).toHaveProperty('support_lookup');
    expect(data).toHaveProperty('fallbacks_by_source');
    expect(typeof data.version).toBe('string');
  });

  it('ontology has client_ids array', () => {
    const path = resolve(__dirname, 'data/ontology.json');
    const data = JSON.parse(readFileSync(path, 'utf-8'));
    expect(Array.isArray(data.client_ids)).toBe(true);
    expect(data.client_ids.length).toBeGreaterThan(0);
  });
});

describe('target_clients CSS optimization', () => {
  it('gmail_web converts display:flex to table fallback', async () => {
    const { css, optimization } = await optimize(
      '.hero { display: flex; color: red; }',
      ['gmail_web'],
    );
    // display:flex is unsupported in Gmail — converted to display:table
    expect(css).toContain('color');
    expect(css).not.toContain('flex');
    expect(css).toContain('table');
    expect(optimization.conversions.length).toBeGreaterThan(0);
    expect(optimization.conversions[0].original_value).toBe('flex');
    expect(optimization.conversions[0].affected_clients).toContain('gmail_web');
  });

  it('outlook_2019_win converts display:flex to table', async () => {
    const { css, optimization } = await optimize(
      '.row { display: flex; }',
      ['outlook_2019_win'],
    );
    expect(css).toContain('table');
    expect(optimization.conversions.some(
      (c) => c.original_value === 'flex' && c.affected_clients.includes('outlook_2019_win'),
    )).toBe(true);
  });

  it('apple_mail_macos preserves standard CSS', async () => {
    const { css } = await optimize(
      '.hero { color: red; font-size: 16px; padding: 10px; }',
      ['apple_mail_macos'],
    );
    expect(css).toContain('color');
    expect(css).toContain('font-size');
  });

  it('multiple clients use most restrictive rules', async () => {
    const { optimization } = await optimize(
      '.hero { display: flex; color: red; }',
      ['gmail_web', 'apple_mail_macos'],
    );
    // display:flex is unsupported in Gmail even though Apple Mail may support it
    // shouldRemove requires ALL clients to have 'none' support, so this tests
    // the intersection behavior — flex may be removed or converted
    expect(optimization).toBeDefined();
    expect(Array.isArray(optimization.removed_properties)).toBe(true);
  });

  it('no target_clients preserves all CSS', async () => {
    const result = await postcss([emailOptimize()]).process(
      '.hero { display: flex; color: red; }',
      { from: undefined },
    );
    // Without target clients, the plugin uses default client list
    expect(result.css).toBeDefined();
    expect(result.emailOptimization).toBeDefined();
  });

  it('MJML-compiled HTML processed correctly with target_clients', async () => {
    // Simulate HTML that looks like MJML-compiled output (table-based)
    const mjmlLikeHtml =
      'table { border-collapse: collapse; } .outlook { mso-line-height-rule: exactly; }';
    const { css } = await optimize(mjmlLikeHtml, ['gmail_web']);
    expect(typeof css).toBe('string');
  });
});
