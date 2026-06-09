#!/usr/bin/env deno run --allow-read

const SCRIPT_DIR = new URL('.', import.meta.url).pathname;
const PROJECT_ROOT = new URL('../../', import.meta.url).pathname;
const INDEX_HTML = `${PROJECT_ROOT}index.html`;
const DEFAULT_OUT_DIR = `${SCRIPT_DIR}out_py_band_compare`;
const outDir = Deno.args[0] || DEFAULT_OUT_DIR;

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        quoted = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      row.push(field);
      field = '';
    } else if (ch === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (ch !== '\r') {
      field += ch;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  if (!rows.length) return [];
  const header = rows[0];
  return rows.slice(1).filter(r => r.some(cell => cell !== '')).map(r => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ''])));
}

function loadBrowserApi() {
  globalThis.localStorage = {getItem() { return null; }, setItem() {}};
  const html = Deno.readTextFileSync(INDEX_HTML);
  let script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  if (!script) throw new Error('No script block found in index.html');
  const cutMarkers = ['$("pathContA").addEventListener', '$("btnBuild").addEventListener'];
  const cut = cutMarkers.map(marker => script.indexOf(marker)).find(index => index >= 0) ?? -1;
  if (cut < 0) throw new Error('Cannot find browser event-listener cut point');
  script = script.slice(0, cut);
  return new Function(`${script}; return {parseCsv, buildFeatureRows, buildEuropeBarTruthRows, runBandRegressions};`)();
}

async function inputFiles() {
  const files = [];
  for await (const entry of Deno.readDir(SCRIPT_DIR)) {
    if (!entry.isFile) continue;
    if (!entry.name.startsWith('vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_')) continue;
    if (!entry.name.endsWith('.csv')) continue;
    if (entry.name.includes('Copy')) continue;
    files.push(`${SCRIPT_DIR}${entry.name}`);
  }
  files.sort();
  if (!files.length) throw new Error('No VK4EMM input CSV files found');
  return files;
}

function key(row) {
  return `${row.date_utc}|${row.band_m}|${row.slot_index}`;
}

function num(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) throw new Error(`Not numeric: ${value}`);
  return n;
}

function checkClose(label, actual, expected, tolerance, failures) {
  const diff = Math.abs(actual - expected);
  if (diff > tolerance) failures.push(`${label}: actual ${actual}, expected ${expected}, diff ${diff}, tolerance ${tolerance}`);
}

const api = loadBrowserApi();
const files = await inputFiles();
const raw = files.flatMap(file => api.parseCsv(Deno.readTextFileSync(file)));
const features = api.buildFeatureRows(raw).filter(row => row.continent === 'Europe');
const truth = api.buildEuropeBarTruthRows(features);
const reg = api.runBandRegressions(truth);

const pyFeatures = parseCsv(Deno.readTextFileSync(`${outDir}/wspr_path_features.csv`));
const pyTruth = parseCsv(Deno.readTextFileSync(`${outDir}/europe_bar_truth.csv`));
const pyPred = parseCsv(Deno.readTextFileSync(`${outDir}/europe_regression_predictions.csv`));

const failures = [];
if (pyFeatures.length !== features.length) failures.push(`feature row count: Python ${pyFeatures.length}, JS ${features.length}`);
if (pyTruth.length !== truth.length) failures.push(`bar-truth row count: Python ${pyTruth.length}, JS ${truth.length}`);
if (pyPred.length !== reg.predictions.length) failures.push(`prediction row count: Python ${pyPred.length}, JS ${reg.predictions.length}`);

const truthMap = new Map(truth.map(row => [key(row), row]));
for (const row of pyTruth) {
  const js = truthMap.get(key(row));
  if (!js) {
    failures.push(`missing JS truth row ${key(row)}`);
    continue;
  }
  for (const field of ['loop2_count', 'loop3_count', 'observation_count']) {
    if (num(row[field]) !== js[field]) failures.push(`${key(row)} ${field}: Python ${row[field]}, JS ${js[field]}`);
  }
  for (const field of ['path_dominance_score', 'dark_delta', 'greyline_delta', 'endpoint_twilight_score']) {
    checkClose(`${key(row)} ${field}`, num(row[field]), js[field], 0.0015, failures);
  }
}

const predMap = new Map(reg.predictions.map(row => [key(row), row]));
for (const row of pyPred) {
  const js = predMap.get(key(row));
  if (!js) {
    failures.push(`missing JS prediction row ${key(row)}`);
    continue;
  }
  checkClose(`${key(row)} simple_model_path_dominance_score`, num(row.simple_model_path_dominance_score), js.simple_model_path_dominance_score, 0.0015, failures);
  checkClose(`${key(row)} model_predicted_loop2_count`, num(row.model_predicted_loop2_count), js.model_predicted_loop2_count, 0.55, failures);
  checkClose(`${key(row)} model_predicted_loop3_count`, num(row.model_predicted_loop3_count), js.model_predicted_loop3_count, 0.55, failures);
}

const summary = {
  inputFiles: files.length,
  rawRows: raw.length,
  featureRows: features.length,
  truthRows: truth.length,
  predictionRows: reg.predictions.length,
  bands: Object.fromEntries(Object.entries(reg.bandModels).map(([band, model]) => [
    band,
    Object.fromEntries(Object.entries(model.paths).map(([pathId, pathModel]) => [
      pathId,
      pathModel.modelBeta ? pathModel.modelBeta.map(v => Number(v.toFixed(6))) : null
    ]))
  ])),
  toleranceNote: 'Python CSV uses compact significant-figure formatting, so decimal comparisons use report tolerances.'
};

if (failures.length) {
  console.log(JSON.stringify(summary, null, 2));
  console.error(`FAIL: ${failures.length} differences found`);
  for (const failure of failures.slice(0, 50)) console.error(`- ${failure}`);
  if (failures.length > 50) console.error(`... ${failures.length - 50} more`);
  Deno.exit(1);
}

console.log(JSON.stringify(summary, null, 2));
console.log('PASS: Python reports and JavaScript calculations agree within report precision.');
