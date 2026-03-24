import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

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
