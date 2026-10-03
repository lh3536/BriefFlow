export const ERROR_MESSAGE = 'Unable to generate brief. Please try again.';

function strings(value) {
  return Array.isArray(value) && value.every((entry) => typeof entry === 'string');
}

export function validateBrief(value) {
  if (!value || !value.preference || !['locations', 'categories', 'keywords', 'exclude_keywords'].every((key) => strings(value.preference[key]))
      || !Array.isArray(value.recommended_items) || value.total_items !== value.recommended_items.length
      || typeof value.summary !== 'string') throw new Error(ERROR_MESSAGE);
  for (const item of value.recommended_items) {
    if (!item || typeof item.title !== 'string' || !strings(item.why_recommended)
        || !Number.isFinite(item.match_score) || !Number.isFinite(item.priority_score)
        || !['location', 'category', 'source', 'deadline'].every((key) => typeof item[key] === 'string')
        || typeof (item.organization ?? item.company) !== 'string') throw new Error(ERROR_MESSAGE);
  }
  return value;
}

export async function generateBrief(userText) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch('/api/brief', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_text: userText }), signal: controller.signal,
    });
    if (!response.ok) throw new Error(ERROR_MESSAGE);
    return validateBrief(await response.json());
  } finally {
    clearTimeout(timer);
  }
}

export function safeSourceUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch {
    return null;
  }
}
