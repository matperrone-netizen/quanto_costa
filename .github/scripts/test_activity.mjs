import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const moduleSource = await readFile(new URL('../../functions/api/activity.js', import.meta.url), 'utf8');
const moduleUrl = `data:text/javascript;base64,${Buffer.from(moduleSource).toString('base64')}`;
const { onRequestPost } = await import(moduleUrl);

const endpoint = 'https://costo-vero.it/api/activity';

async function invoke({ body = '{"event":"calculation"}', origin = 'https://costo-vero.it', contentType = 'application/json' } = {}) {
  const headers = {};
  if (origin !== null) headers.Origin = origin;
  if (contentType !== null) headers['Content-Type'] = contentType;
  const points = [];
  const response = await onRequestPost({
    request: new Request(endpoint, { method: 'POST', headers, body }),
    env: { ACTIVITY_EVENTS: { writeDataPoint: point => points.push(point) } }
  });
  return { response, points };
}

const valid = await invoke();
assert.equal(valid.response.status, 204);
assert.equal(valid.response.headers.get('Cache-Control'), 'no-store');
assert.deepEqual(valid.points, [{ blobs: ['calculation'], doubles: [], indexes: [] }]);

const fuelCalculation = await invoke({ body: '{"event":"fuel_calculation"}' });
assert.equal(fuelCalculation.response.status, 204);
assert.deepEqual(fuelCalculation.points, [{ blobs: ['fuel_calculation'], doubles: [], indexes: [] }]);

const mortgageCalculation = await invoke({ body: '{"event":"mortgage_calculation"}' });
assert.equal(mortgageCalculation.response.status, 204);
assert.deepEqual(mortgageCalculation.points, [{ blobs: ['mortgage_calculation'], doubles: [], indexes: [] }]);

const childCostCalculation = await invoke({ body: '{"event":"child_cost_calculation"}' });
assert.equal(childCostCalculation.response.status, 204);
assert.deepEqual(childCostCalculation.points, [{ blobs: ['child_cost_calculation'], doubles: [], indexes: [] }]);

for (const test of [
  { input: { origin: null }, status: 403 },
  { input: { origin: 'https://example.com' }, status: 403 },
  { input: { contentType: 'text/plain' }, status: 415 },
  { input: { body: '{invalid' }, status: 400 },
  { input: { body: '{"event":"unknown"}' }, status: 400 },
  { input: { body: JSON.stringify({ event: 'calculation', padding: 'x'.repeat(128) }) }, status: 413 }
]) {
  const result = await invoke(test.input);
  assert.equal(result.response.status, test.status);
  assert.equal(result.points.length, 0);
  assert.equal(result.response.headers.get('Cache-Control'), 'no-store');
}

console.log('Activity endpoint: 10 casi superati.');
