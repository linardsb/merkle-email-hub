import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import postcss from 'postcss';

const __dirname = dirname(fileURLToPath(import.meta.url));

const TEMPLATE_DIR = resolve(__dirname, '../../app/ai/templates/library');
function loadTemplate(name) {
  return readFileSync(resolve(TEMPLATE_DIR, `${name}.html`), 'utf-8');
}

describe('isPreCompiledEmail', () => {
  let isPreCompiledEmail;

  beforeAll(async () => {
    const mod = await import('./precompiled-detect.js');
    isPreCompiledEmail = mod.isPreCompiledEmail;
  });

  it('detects golden templates as pre-compiled', () => {
    const html = loadTemplate('promotional_hero');
    expect(isPreCompiledEmail(html)).toBe(true);
  });

  it('detects multiple golden templates as pre-compiled', () => {
    for (const name of ['newsletter_2col', 'transactional_receipt', 'minimal_text']) {
      expect(isPreCompiledEmail(loadTemplate(name))).toBe(true);
    }
  });

  it('rejects Maizzle template source', () => {
    const maizzle = `<extends src="layouts/default.html"><block name="content"><p>Hello</p></block></extends>`;
    expect(isPreCompiledEmail(maizzle)).toBe(false);
  });

  it('rejects HTML with <x- custom tags', () => {
    const source = `<!DOCTYPE html><html><body><x-header>Logo</x-header></body></html>`;
    expect(isPreCompiledEmail(source)).toBe(false);
  });

  it('rejects plain HTML without inline styles', () => {
    const source = `<!DOCTYPE html><html><body><table role="presentation"><tr><td>Hi</td></tr></table><table role="presentation"><tr><td>Bye</td></tr></table></body></html>`;
    expect(isPreCompiledEmail(source)).toBe(false);
  });

  it('rejects HTML fragment without document shell', () => {
    const source = `<table role="presentation" cellpadding="0"><tr><td style="color:red">A</td></tr></table><table role="presentation" cellpadding="0"><tr><td style="padding:10px">B</td></tr></table><p style="margin:0">C</p>`;
    expect(isPreCompiledEmail(source)).toBe(false);
  });

  it('rejects HTML without table layout', () => {
    const source = `<!DOCTYPE html><html><body><div style="color:red">A</div><div style="padding:10px">B</div><p style="margin:0">C</p></body></html>`;
    expect(isPreCompiledEmail(source)).toBe(false);
  });
});

describe('postcss-email-optimize shorthand expansion', () => {
  let emailOptimize;

  beforeAll(async () => {
    const mod = await import('./postcss-email-optimize.js');
    emailOptimize = mod.default;
  });

  it('expands font shorthand into longhands', async () => {
    const css = '.test { font: 700 32px/40px Inter, sans-serif; }';
    const result = await postcss([emailOptimize()]).process(css, { from: undefined });
    expect(result.css).toContain('font-weight');
    expect(result.css).toContain('font-size');
    expect(result.css).toContain('font-family');
    expect(result.emailOptimization.shorthand_expansions).toBeGreaterThan(0);
  });

  it('expands padding shorthand into 4 longhands', async () => {
    const css = '.test { padding: 16px 32px; }';
    const result = await postcss([emailOptimize()]).process(css, { from: undefined });
    expect(result.css).toContain('padding-top');
    expect(result.css).toContain('padding-right');
    expect(result.css).toContain('padding-bottom');
    expect(result.css).toContain('padding-left');
  });

  it('preserves url with colon in background', async () => {
    const css = '.test { background: url(https://example.com/img.png) no-repeat; }';
    const result = await postcss([emailOptimize()]).process(css, { from: undefined });
    expect(result.css).toContain('https://example.com/img.png');
  });

  it('extracts responsive breakpoints from @media', async () => {
    const css = '@media (max-width: 600px) { .mobile { font-size: 14px; } }';
    const result = await postcss([emailOptimize()]).process(css, { from: undefined });
    expect(result.emailOptimization.responsive).toContain('600px');
    // @media rule is preserved
    expect(result.css).toContain('@media');
  });

  it('reports shorthand expansions count', async () => {
    const css = '.a { margin: 10px; } .b { padding: 5px 10px; }';
    const result = await postcss([emailOptimize()]).process(css, { from: undefined });
    expect(result.emailOptimization.shorthand_expansions).toBeGreaterThanOrEqual(8);
  });
});
