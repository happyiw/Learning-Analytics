const baseUrl = process.env.BASE_URL || 'http://localhost:8000';
const total = Number(process.env.REQUESTS || 100);
const concurrency = Number(process.env.CONCURRENCY || 10);
const path = process.env.PATH_TO_TEST || '/';
const token = process.env.ACCESS_TOKEN || '';

let next = 0;
let errors = 0;
const timings = [];
const started = performance.now();

async function worker() {
  while (true) {
    const index = next++;
    if (index >= total) return;
    const requestStarted = performance.now();
    try {
      const response = await fetch(`${baseUrl}${path}`, {
        headers: token ? { authorization: `Bearer ${token}` } : {}
      });
      await response.arrayBuffer();
      if (!response.ok) errors++;
    } catch {
      errors++;
    }
    timings.push(performance.now() - requestStarted);
  }
}

await Promise.all(Array.from({ length: concurrency }, worker));
const elapsed = performance.now() - started;
timings.sort((left, right) => left - right);
const percentile = (value) => timings[Math.min(timings.length - 1, Math.floor(timings.length * value))];

console.log(JSON.stringify({
  path,
  total,
  concurrency,
  errors,
  seconds: +(elapsed / 1000).toFixed(2),
  rps: +(total / (elapsed / 1000)).toFixed(2),
  average_ms: +(timings.reduce((sum, value) => sum + value, 0) / timings.length).toFixed(1),
  p50_ms: +percentile(0.5).toFixed(1),
  p95_ms: +percentile(0.95).toFixed(1),
  max_ms: +timings[timings.length - 1].toFixed(1)
}, null, 2));
