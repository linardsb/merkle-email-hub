import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const TEMPLATE_DIR = resolve(__dirname, '../../app/ai/templates/library');

function loadTemplate(name) {
  return readFileSync(resolve(TEMPLATE_DIR, `${name}.html`), 'utf-8');
}

describe('isPreCompiledEmail — extended coverage', () => {
  let isPreCompiledEmail;

  beforeAll(async () => {
    const mod = await import('./precompiled-detect.js');
    isPreCompiledEmail = mod.isPreCompiledEmail;
  });

  it('returns true for newsletter template', () => {
    expect(isPreCompiledEmail(loadTemplate('newsletter_1col'))).toBe(true);
  });

  it('all golden templates detected as pre-compiled', () => {
    const templates = [
      'promotional_hero', 'promotional_grid', 'promotional_split',
      'newsletter_1col', 'newsletter_2col',
      'transactional_receipt', 'minimal_text',
      'announcement_company', 'announcement_product',
      'event_invitation', 'event_reminder',
      'retention_survey', 'retention_winback',
    ];
    for (const name of templates) {
      expect(isPreCompiledEmail(loadTemplate(name)), `${name} should be pre-compiled`).toBe(true);
    }
  });
});
