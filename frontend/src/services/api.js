let bearer = null;
let expired = () => {};
export function setSession(token, onExpire) {
  bearer = token;
  if (onExpire) expired = onExpire;
}
const base = import.meta.env.VITE_API_URL || '/api';
export function params(values) {
  return new URLSearchParams(
    Object.entries(values).filter(([, v]) => v !== '' && v !== null && v !== undefined),
  ).toString();
}
export async function api(path, options = {}) {
  const headers = { ...(bearer ? { Authorization: `Bearer ${bearer}` } : {}), ...options.headers };
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !(options.body instanceof URLSearchParams)
  ) {
    headers['Content-Type'] = 'application/json';
    options = { ...options, body: JSON.stringify(options.body) };
  }
  const response = await fetch(base + path, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/login')) expired();
    const body = await response.json().catch(() => ({}));
    throw new Error(
      Array.isArray(body.detail)
        ? body.detail.map((e) => `${e.loc.slice(1).join(' ')}: ${e.msg}`).join('; ')
        : body.detail || 'Request failed',
    );
  }
  if (
    options.method &&
    options.method !== 'GET' &&
    !path.startsWith('/auth') &&
    !path.endsWith('/identity')
  ) {
    window.dispatchEvent(new Event('postmate:records-changed'));
  }
  if (options.preview)
    return {
      blob: await response.blob(),
      pageCount: Number(response.headers.get('X-Page-Count') || 1),
    };
  return response.status === 204 ? null : options.download ? response.blob() : response.json();
}
export async function download(path, filename) {
  const blob = await api(path, { download: true });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
