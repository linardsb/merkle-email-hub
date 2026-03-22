import { describe, it, expect } from 'vitest';
import postcss from 'postcss';
import emailOptimize from './postcss-email-optimize.js';

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
});
