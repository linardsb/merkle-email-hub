import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
let ontologyData = null;

function loadOntology() {
  if (ontologyData) return ontologyData;
  ontologyData = JSON.parse(readFileSync(resolve(__dirname, 'data/ontology.json'), 'utf-8'));
  return ontologyData;
}

function findPropertyId(ontology, propName, value) {
  const entries = ontology.properties_by_name[propName];
  if (!entries) return null;
  if (value) {
    const first = value.trim().split(/\s/)[0];
    const specific = entries.find(e => e.value === first);
    if (specific) return specific.id;
  }
  return (entries.find(e => e.value === null) || entries[0])?.id || null;
}

function getSupport(ontology, propertyId, clientId) {
  return ontology.support_lookup[`${propertyId}::${clientId}`] || 'full';
}

function shouldRemove(ontology, propertyId, targetClients) {
  if (!targetClients.every(c => getSupport(ontology, propertyId, c) === 'none')) return false;
  const fb = ontology.fallbacks_by_source[propertyId];
  return !fb || fb.length === 0;
}

function getConversions(ontology, propertyId, targetClients) {
  const unsupported = targetClients.filter(c => getSupport(ontology, propertyId, c) === 'none');
  if (!unsupported.length) return [];
  const fallbacks = ontology.fallbacks_by_source[propertyId];
  if (!fallbacks) return [];

  const result = [];
  for (const fb of fallbacks) {
    let affected = unsupported;
    if (fb.client_ids.length > 0) {
      affected = unsupported.filter(c => fb.client_ids.includes(c));
      if (!affected.length) continue;
    }
    if (fb.target_property_name) {
      result.push({
        replacement_property: fb.target_property_name,
        replacement_value: fb.target_value || '',
        reason: fb.technique || 'Fallback',
        affected_clients: affected,
      });
    }
  }
  return result;
}

/**
 * Expand CSS shorthand properties into their longhand equivalents.
 * This normalizes shorthands so the ontology can evaluate each property individually.
 */
function expandShorthands(root) {
  let count = 0;

  root.walkDecls((decl) => {
    const prop = decl.prop.toLowerCase();
    let replacements = null;

    if (prop === 'padding' || prop === 'margin') {
      replacements = expandBoxShorthand(prop, decl.value);
    } else if (prop === 'border') {
      replacements = expandBorderShorthand(decl.value);
    } else if (prop === 'background') {
      replacements = expandBackgroundShorthand(decl.value);
    } else if (prop === 'font') {
      replacements = expandFontShorthand(decl.value);
    }

    if (replacements && replacements.length > 0) {
      count += replacements.length;
      for (const [p, v] of replacements) {
        decl.before({ prop: p, value: v });
      }
      decl.remove();
    }
  });

  return count;
}

function expandBoxShorthand(prop, value) {
  const parts = value.trim().split(/\s+/);
  let top, right, bottom, left;
  if (parts.length === 1) {
    top = right = bottom = left = parts[0];
  } else if (parts.length === 2) {
    top = bottom = parts[0];
    right = left = parts[1];
  } else if (parts.length === 3) {
    top = parts[0]; right = parts[1]; bottom = parts[2]; left = parts[1];
  } else {
    top = parts[0]; right = parts[1]; bottom = parts[2]; left = parts[3];
  }
  return [
    [`${prop}-top`, top],
    [`${prop}-right`, right],
    [`${prop}-bottom`, bottom],
    [`${prop}-left`, left],
  ];
}

function expandBorderShorthand(value) {
  const parts = value.trim().split(/\s+/);
  const result = [];
  const styles = new Set(['none','hidden','dotted','dashed','solid','double','groove','ridge','inset','outset']);
  for (const part of parts) {
    if (/^\d/.test(part)) {
      result.push(['border-width', part]);
    } else if (styles.has(part)) {
      result.push(['border-style', part]);
    } else {
      result.push(['border-color', part]);
    }
  }
  return result.length > 0 ? result : null;
}

function expandBackgroundShorthand(value) {
  const result = [];
  // Extract url()
  const urlMatch = value.match(/url\([^)]*\)/i);
  if (urlMatch) {
    result.push(['background-image', urlMatch[0]]);
  }
  // Extract color (hex, rgb, named)
  const colorMatch = value.match(/#[0-9a-fA-F]{3,8}|rgb[a]?\([^)]*\)/i);
  if (colorMatch) {
    result.push(['background-color', colorMatch[0]]);
  } else if (!urlMatch) {
    // If no url and no explicit color, the whole value might be a color keyword
    const keywords = new Set(['transparent','none','inherit','initial','unset']);
    const remaining = value.replace(/url\([^)]*\)/gi, '').trim();
    if (remaining && !keywords.has(remaining)) {
      // Check if it's a single color keyword
      const parts = remaining.split(/\s+/);
      const repeatWords = new Set(['repeat','no-repeat','repeat-x','repeat-y','space','round']);
      const posWords = new Set(['top','bottom','left','right','center']);
      const nonColorParts = parts.filter(p => repeatWords.has(p) || posWords.has(p) || /^\d/.test(p));
      if (nonColorParts.length < parts.length) {
        const colorPart = parts.find(p => !repeatWords.has(p) && !posWords.has(p) && !/^\d/.test(p));
        if (colorPart) result.push(['background-color', colorPart]);
      }
    }
  }
  // Extract repeat
  const repeatMatch = value.match(/\b(repeat|no-repeat|repeat-x|repeat-y|space|round)\b/);
  if (repeatMatch) result.push(['background-repeat', repeatMatch[1]]);
  // Extract position
  const posMatch = value.match(/\b(top|bottom|left|right|center)\b/);
  if (posMatch) result.push(['background-position', posMatch[1]]);
  return result.length > 0 ? result : null;
}

function expandFontShorthand(value) {
  // font: [style] [variant] [weight] size[/line-height] family
  const re = /^(italic|oblique)?\s*(small-caps)?\s*(bold|bolder|lighter|normal|\d{3})?\s*(\d+[\w%]+)\s*(?:\/\s*([\d.]+[\w%]*))?[\s,]+(.+)$/i;
  const m = value.trim().match(re);
  if (!m) return null;
  const result = [];
  if (m[1]) result.push(['font-style', m[1]]);
  if (m[2]) result.push(['font-variant', m[2]]);
  if (m[3]) result.push(['font-weight', m[3]]);
  result.push(['font-size', m[4]]);
  if (m[5]) result.push(['line-height', m[5]]);
  result.push(['font-family', m[6].trim()]);
  return result;
}

const REMOVE_AT_RULES = new Set(['charset', 'layer', 'import', 'namespace']);

const plugin = (opts = {}) => {
  const targetClients = opts.targetClients || ['gmail_web', 'outlook_365_win', 'apple_mail_macos', 'yahoo_web'];
  const ontology = loadOntology();
  const removed = [];
  const conversions = [];
  const warnings = [];
  const responsive = [];
  let shorthandExpansions = 0;

  return {
    postcssPlugin: 'postcss-email-optimize',

    Once(root) {
      shorthandExpansions = expandShorthands(root);
    },

    Declaration(decl, { result }) {
      const propertyId = findPropertyId(ontology, decl.prop, decl.value);
      if (!propertyId) return;

      if (shouldRemove(ontology, propertyId, targetClients)) {
        removed.push(`${decl.prop}: ${decl.value}`);
        result.messages.push({ type: 'email-optimize', subtype: 'removed', property: decl.prop });
        decl.remove();
        return;
      }

      const convs = getConversions(ontology, propertyId, targetClients);
      if (convs.length > 0) {
        const first = convs[0];
        conversions.push({
          original_property: decl.prop, original_value: decl.value,
          replacement_property: first.replacement_property,
          replacement_value: first.replacement_value || decl.value,
          reason: first.reason, affected_clients: first.affected_clients,
        });
        decl.prop = first.replacement_property;
        if (first.replacement_value) decl.value = first.replacement_value;
      }

      const partial = targetClients.filter(c => getSupport(ontology, propertyId, c) === 'partial');
      if (partial.length) warnings.push(`${decl.prop}: partial support in ${partial.join(', ')}`);
    },

    AtRule(atRule) {
      if (REMOVE_AT_RULES.has(atRule.name.toLowerCase())) {
        warnings.push(`Removed @${atRule.name}`);
        atRule.remove();
        return;
      }
      // Extract responsive breakpoints from @media rules (preserve the rule)
      if (atRule.name === 'media') {
        const bpMatch = atRule.params.match(/max-width:\s*(\d+px)/);
        if (bpMatch && !responsive.includes(bpMatch[1])) {
          responsive.push(bpMatch[1]);
        }
      }
    },

    OnceExit(root, { result }) {
      result.emailOptimization = {
        removed_properties: removed,
        conversions,
        warnings,
        shorthand_expansions: shorthandExpansions,
        responsive,
      };
    },
  };
};

plugin.postcss = true;
export default plugin;
export { loadOntology };
