import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_SRC = resolve(__dirname, '../../../app/knowledge/ontology/data');
const DATA_DEST = resolve(__dirname, '../data');

function loadYaml(filename) {
  return yaml.load(readFileSync(resolve(DATA_SRC, filename), 'utf-8'));
}

function buildOptimized() {
  const clientsData = loadYaml('clients.yaml');
  const propsData = loadYaml('css_properties.yaml');
  const supportData = loadYaml('support_matrix.yaml');
  const fallbacksData = loadYaml('fallbacks.yaml');

  // Index properties by CSS name for fast Declaration lookup
  const propertiesByName = {};
  for (const p of propsData.properties) {
    if (!propertiesByName[p.property_name]) propertiesByName[p.property_name] = [];
    propertiesByName[p.property_name].push({ id: p.id, value: p.value || null, category: p.category });
  }

  // Sparse support: only none/partial stored (absent = full)
  const supportLookup = {};
  for (const s of (supportData.support || [])) {
    supportLookup[`${s.property_id}::${s.client_id}`] = s.level;
  }

  // Fallbacks indexed by source_property_id, with resolved target names
  const fallbacksBySource = {};
  for (const f of (fallbacksData.fallbacks || [])) {
    if (!fallbacksBySource[f.source_property_id]) fallbacksBySource[f.source_property_id] = [];
    const target = propsData.properties.find(p => p.id === f.target_property_id);
    fallbacksBySource[f.source_property_id].push({
      target_property_name: target?.property_name || null,
      target_value: target?.value || null,
      client_ids: f.client_ids || [],
      technique: f.technique || null,
    });
  }

  return {
    version: new Date().toISOString(),
    client_ids: clientsData.clients.map(c => c.id),
    properties_by_name: propertiesByName,
    support_lookup: supportLookup,
    fallbacks_by_source: fallbacksBySource,
  };
}

mkdirSync(DATA_DEST, { recursive: true });
const ontology = buildOptimized();
const outPath = resolve(DATA_DEST, 'ontology.json');
writeFileSync(outPath, JSON.stringify(ontology, null, 2));

const propCount = Object.values(ontology.properties_by_name).flat().length;
console.log(`Ontology synced: ${propCount} properties, ${Object.keys(ontology.support_lookup).length} support entries → ${outPath}`);
