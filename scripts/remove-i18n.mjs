#!/usr/bin/env node
/**
 * Codemod: Remove next-intl from the codebase.
 * Replaces all t("key") calls with inlined English strings from en.json.
 * Run: node scripts/remove-i18n.mjs
 */

import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const SRC = path.join(ROOT, "cms/apps/web/src");
const EN = JSON.parse(
  fs.readFileSync(path.join(ROOT, "cms/apps/web/messages/en.json"), "utf8"),
);

/** Resolve a dotted key from the EN object. Returns undefined if missing. */
function resolve(ns, key) {
  const parts = [...(ns ? ns.split(".") : []), ...key.split(".")];
  let cur = EN;
  for (const p of parts) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = cur[p];
  }
  return typeof cur === "string" ? cur : undefined;
}

/** Escape backtick-template characters */
function esc(s) {
  return s.replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\$/g, "\\$");
}

/**
 * Convert an ICU message with interpolations to a JS template literal.
 * Handles {var} placeholders and one plural pattern.
 * @param {string} msg  - English ICU string
 * @param {string} argsStr - raw text inside the second t() argument, e.g. `{ count: warningCount }`
 * @returns {string} JS expression (template literal or string literal)
 */
function icuToTemplate(msg, argsStr) {
  // Build a map from ICU var name → JS expression
  const varMap = {};
  if (argsStr) {
    // Parse { key: expr, key2, key3: expr3 }
    const inner = argsStr.replace(/^\{/, "").replace(/\}$/, "").trim();
    // Split on commas that are not inside nested braces
    let depth = 0;
    let current = "";
    const parts = [];
    for (const ch of inner) {
      if (ch === "{") depth++;
      if (ch === "}") depth--;
      if (ch === "," && depth === 0) {
        parts.push(current.trim());
        current = "";
      } else {
        current += ch;
      }
    }
    if (current.trim()) parts.push(current.trim());

    for (const part of parts) {
      const colonIdx = part.indexOf(":");
      if (colonIdx === -1) {
        // shorthand { foo } → foo: foo
        const name = part.trim();
        varMap[name] = name;
      } else {
        const name = part.slice(0, colonIdx).trim();
        const expr = part.slice(colonIdx + 1).trim();
        varMap[name] = expr;
      }
    }
  }

  // Check for ICU plural: {count, plural, one {X} other {Y}}
  const pluralRe = /\{(\w+),\s*plural,\s*one\s*\{([^}]*)\}\s*other\s*\{([^}]*)\}\}/;
  let processed = msg;
  const pluralMatch = processed.match(pluralRe);
  if (pluralMatch) {
    const [full, varName, one, other] = pluralMatch;
    const jsVar = varMap[varName] || varName;
    const replacement = `\${${jsVar} === 1 ? "${one}" : "${other}"}`;
    processed = processed.replace(full, replacement);
  }

  // Replace remaining {var} placeholders
  processed = processed.replace(/\{(\w+)\}/g, (_, name) => {
    const jsExpr = varMap[name] || name;
    return `\${${jsExpr}}`;
  });

  // If no interpolations, return a simple string
  if (!processed.includes("${")) {
    return `"${processed.replace(/"/g, '\\"')}"`;
  }

  return `\`${esc(processed).replace(/\$\{/g, "${")}\``;
}

/** Walk directory for .ts/.tsx files */
function walk(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(full));
    } else if (/\.(tsx?)$/.test(entry.name)) {
      results.push(full);
    }
  }
  return results;
}

let filesModified = 0;
let totalReplacements = 0;
const warnings = [];

for (const file of walk(SRC)) {
  let src = fs.readFileSync(file, "utf8");
  const relPath = path.relative(ROOT, file);

  // Skip files that don't use next-intl
  if (
    !src.includes("next-intl") &&
    !src.includes("useTranslations") &&
    !src.includes("getTranslations")
  ) {
    continue;
  }

  let modified = false;
  let namespace = null;

  // 1. Extract namespace from useTranslations("ns") or getTranslations("ns")
  const nsMatch = src.match(
    /(?:useTranslations|(?:await\s+)?getTranslations)\(\s*"([^"]+)"\s*\)/,
  );
  if (nsMatch) {
    namespace = nsMatch[1];
  }

  // 2. Remove import lines for next-intl
  const importRe =
    /^import\s+\{[^}]*\}\s+from\s+["']next-intl(?:\/server)?["'];?\s*\n/gm;
  if (importRe.test(src)) {
    src = src.replace(importRe, "");
    modified = true;
  }

  // 3. Remove const t = useTranslations(...) or const t = await getTranslations(...)
  const tDeclRe =
    /^\s*const\s+t\s*=\s*(?:await\s+)?(?:useTranslations|getTranslations)\([^)]*\);?\s*\n/gm;
  if (tDeclRe.test(src)) {
    src = src.replace(tDeclRe, "");
    modified = true;
  }

  // 4. Replace t("key") and t("key", { ... }) calls
  // Use a manual parser approach for robustness
  let replacements = 0;
  let output = "";
  let i = 0;

  while (i < src.length) {
    // Look for t( pattern — but only standalone 't' (not part of another identifier)
    if (
      src[i] === "t" &&
      src[i + 1] === "(" &&
      (i === 0 || !/[\w$]/.test(src[i - 1]))
    ) {
      // Find the matching closing paren
      let depth = 1;
      let j = i + 2;
      while (j < src.length && depth > 0) {
        if (src[j] === "(") depth++;
        if (src[j] === ")") depth--;
        if (src[j] === '"' || src[j] === "'" || src[j] === "`") {
          // Skip string
          const quote = src[j];
          j++;
          while (j < src.length && src[j] !== quote) {
            if (src[j] === "\\") j++;
            j++;
          }
        }
        j++;
      }

      const callContent = src.slice(i + 2, j - 1).trim();

      // Parse the arguments: first arg is the key (string), optional second arg is params object
      // Find the key string
      const keyMatch = callContent.match(/^"([^"]+)"/);
      if (keyMatch) {
        const key = keyMatch[1];
        const afterKey = callContent.slice(keyMatch[0].length).trim();

        let argsStr = null;
        if (afterKey.startsWith(",")) {
          argsStr = afterKey.slice(1).trim();
          // Remove defaultValue from argsStr if present, but capture it as fallback
          // Pattern: { defaultValue: "..." } or { defaultValue: expr, ...rest }
        }

        // Check if this is a dynamic key pattern (template literal) — skip for now
        const englishStr = resolve(namespace, key);

        if (englishStr !== undefined) {
          const replacement = icuToTemplate(englishStr, argsStr);
          output += replacement;
          replacements++;
          i = j;
          continue;
        } else {
          // Key not found — leave a TODO
          warnings.push(`${relPath}: missing key "${namespace}.${key}"`);
          output += `/* TODO: missing i18n key: ${namespace}.${key} */ t(${callContent})`;
          i = j;
          continue;
        }
      } else if (callContent.startsWith("`")) {
        // Dynamic key — skip, leave as-is with a TODO comment
        warnings.push(`${relPath}: dynamic key pattern — needs manual fix`);
        output += `/* TODO: dynamic i18n key */ t(${callContent})`;
        i = j;
        replacements++;
        continue;
      } else {
        // Not a recognized pattern, leave as-is
        output += src.slice(i, j);
        i = j;
        continue;
      }
    } else {
      output += src[i];
      i++;
    }
  }

  if (replacements > 0) {
    src = output;
    modified = true;
    totalReplacements += replacements;
  }

  if (modified) {
    fs.writeFileSync(file, src);
    filesModified++;
    console.log(`  ✓ ${relPath} (${replacements} replacements)`);
  }
}

console.log(
  `\nDone: ${filesModified} files modified, ${totalReplacements} replacements`,
);
if (warnings.length > 0) {
  console.log(`\nWarnings (${warnings.length}):`);
  for (const w of warnings) {
    console.log(`  ⚠ ${w}`);
  }
}
