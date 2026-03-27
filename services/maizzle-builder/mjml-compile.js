/**
 * Pure MJML compilation wrapper with email-optimized defaults.
 *
 * Extracted as a standalone module so it can be unit-tested via Vitest
 * without needing to spin up the Express server.
 */

import mjml2html from "mjml";
import { readFileSync } from "node:fs";

const mjmlPkg = JSON.parse(
  readFileSync(new URL("./node_modules/mjml/package.json", import.meta.url), "utf-8"),
);

/** Installed MJML version string (e.g. "4.18.0"). */
export const mjmlVersion = mjmlPkg.version;

/**
 * Compile an MJML string to HTML.
 *
 * @param {string} mjmlStr  – MJML markup
 * @param {object} [options]
 * @param {"strict"|"soft"|"skip"} [options.validationLevel] – MJML validation (default "soft")
 * @returns {{ html: string, errors: Array<{ line: number, message: string, tagName: string }> }}
 */
export function compileMjml(mjmlStr, options = {}) {
  return mjml2html(mjmlStr, {
    keepComments: false,
    validationLevel: options.validationLevel || "soft",
    fonts: {},
  });
}
