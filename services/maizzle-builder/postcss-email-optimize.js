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

const REMOVE_AT_RULES = new Set(['charset', 'layer', 'import', 'namespace']);

const plugin = (opts = {}) => {
  const targetClients = opts.targetClients || ['gmail_web', 'outlook_365_win', 'apple_mail_macos', 'yahoo_web'];
  const ontology = loadOntology();
  const removed = [];
  const conversions = [];
  const warnings = [];

  return {
    postcssPlugin: 'postcss-email-optimize',

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
      }
    },

    OnceExit(root, { result }) {
      result.emailOptimization = { removed_properties: removed, conversions, warnings };
    },
  };
};

plugin.postcss = true;
export default plugin;
export { loadOntology };
