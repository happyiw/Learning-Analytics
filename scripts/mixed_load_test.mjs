const baseUrl = process.env.BASE_URL || 'http://localhost:8000';
const total = Number(process.env.REQUESTS || 2000);
const concurrency = Number(process.env.CONCURRENCY || 30);
const studentCount = Number(process.env.STUDENT_TOKENS || 50);
const loginConcurrency = Number(process.env.LOGIN_CONCURRENCY || 10);

async function login(username, password) {
  const response = await fetch(`${baseUrl}/api/auth/login/`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (!response.ok) throw new Error(`Login failed for ${username}: ${response.status}`);
  return (await response.json()).access_token;
}

async function mapWithConcurrency(items, limit, mapper) {
  const output = new Array(items.length);
  let cursor = 0;
  async function worker() {
    while (true) {
      const index = cursor++;
      if (index >= items.length) return;
      output[index] = await mapper(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return output;
}

const studentTokens = await mapWithConcurrency(
  Array.from({ length: studentCount }, (_, index) => index),
  loginConcurrency,
  (index) => login(`load_medium_${String(index + 1).padStart(5, '0')}`, 'loadpass')
);
const teacherToken = await login('teacher', 'teacher');

let next = 0;
let writeIndex = 0;
const results = new Map();
const started = performance.now();

function record(label, elapsed, status) {
  const bucket = results.get(label) || { timings: [], errors: 0, requests: 0 };
  bucket.timings.push(elapsed);
  bucket.requests++;
  if (status >= 400 || status === 0) bucket.errors++;
  results.set(label, bucket);
}

function scenario(index) {
  const percentile = index % 100;
  const studentIndex = index % studentTokens.length;
  const studentToken = studentTokens[studentIndex];
  const courseId = 10000 + studentIndex % 20;
  if (percentile < 45) {
    return ['student_snapshot', '/api/analytics/my/snapshot/', 'GET', studentToken];
  }
  if (percentile < 65) {
    return ['recommendations', '/api/recommendations/my/', 'GET', studentToken];
  }
  if (percentile < 85) {
    return ['teacher_dashboard', '/api/teacher/courses/10000/dashboard/', 'GET', teacherToken];
  }
  if (percentile < 95) {
    return ['course_progress', `/api/courses/${courseId}/progress/my/`, 'GET', studentToken];
  }

  const currentWrite = writeIndex++;
  const writer = currentWrite % studentTokens.length;
  const writerCourse = writer % 20;
  const moduleIndex = Math.floor(currentWrite / studentTokens.length) % 15;
  const lessonIndex = 4 + Math.floor(currentWrite / (studentTokens.length * 15)) % 2;
  const lessonId = 1000000 + (writerCourse * 15 + moduleIndex) * 6 + lessonIndex;
  return ['lesson_complete', `/api/lessons/${lessonId}/complete/`, 'POST', studentTokens[writer]];
}

async function worker() {
  while (true) {
    const index = next++;
    if (index >= total) return;
    const [label, path, method, token] = scenario(index);
    const requestStarted = performance.now();
    let status = 0;
    try {
      const response = await fetch(`${baseUrl}${path}`, {
        method,
        headers: { authorization: `Bearer ${token}` }
      });
      status = response.status;
      await response.arrayBuffer();
    } catch {
      status = 0;
    }
    record(label, performance.now() - requestStarted, status);
  }
}

await Promise.all(Array.from({ length: concurrency }, worker));
const elapsed = performance.now() - started;

const summary = [];
for (const [label, bucket] of results.entries()) {
  bucket.timings.sort((left, right) => left - right);
  const at = (value) => bucket.timings[Math.min(bucket.timings.length - 1, Math.floor(bucket.timings.length * value))];
  summary.push({
    label,
    requests: bucket.requests,
    errors: bucket.errors,
    average_ms: +(bucket.timings.reduce((sum, value) => sum + value, 0) / bucket.timings.length).toFixed(1),
    p50_ms: +at(0.50).toFixed(1),
    p95_ms: +at(0.95).toFixed(1),
    p99_ms: +at(0.99).toFixed(1),
    max_ms: +bucket.timings[bucket.timings.length - 1].toFixed(1)
  });
}

console.log(JSON.stringify({
  total,
  concurrency,
  seconds: +(elapsed / 1000).toFixed(2),
  rps: +(total / (elapsed / 1000)).toFixed(2),
  scenarios: summary.sort((left, right) => left.label.localeCompare(right.label))
}, null, 2));
