// SABIGOZAR Deploy Panel · shared helpers · @SAHEBKARAMI
export const RW = "https://backboard.railway.app/graphql/v2";
export const CF = "https://api.cloudflare.com/client/v4";
export const GH = "https://api.github.com";
export const MOUNT = "/var/lib/sabigozar", HTTP_PORT = 8080, REALITY_PORT = 8443;
export const REGIONS = { "europe-west4-drams3a": "EU West (Amsterdam)", "us-west2": "US West", "us-east4-eqdc4a": "US East", "asia-southeast1-eqsg3a": "Singapore" };
export class StepError extends Error {}
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const edges = (x) => ((x && x.edges) || []).map((e) => e.node);

export async function gql(token, query, variables = {}, soft = false) {
  const r = await fetch(RW, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ query, variables }) });
  let j;
  try { j = await r.json(); } catch { throw new StepError(`Railway API ${r.status}`); }
  if (j.errors && !soft) throw new StepError("Railway: " + j.errors.map((e) => e.message).join("; "));
  return soft ? { data: j.data || {}, errors: j.errors } : j.data || {};
}

export async function cf(token, method, path, body) {
  const r = await fetch(CF + path, { method, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: body ? JSON.stringify(body) : undefined });
  let j;
  try { j = await r.json(); } catch { throw new StepError(`Cloudflare ${r.status}`); }
  if (!j.success) throw new StepError(`Cloudflare ${method} ${path.split("?")[0]}: ` + (j.errors || []).map((e) => e.message).join("; "));
  return j.result;
}

export async function gh(token, method, path, body) {
  const h = { Accept: "application/vnd.github+json", "User-Agent": "sabigozar-panel" };
  if (token) h.Authorization = `Bearer ${token}`;
  if (body) h["Content-Type"] = "application/json";
  const r = await fetch(GH + path, { method, headers: h, body: body ? JSON.stringify(body) : undefined });
  let j = {};
  try { j = await r.json(); } catch {}
  return { status: r.status, j };
}

export function strongPassword(n = 18) {
  const U = "ABCDEFGHJKLMNPQRSTUVWXYZ", L = "abcdefghijkmnpqrstuvwxyz", D = "23456789", S = "!@#%^*-_=+";
  const rnd = (s) => s[crypto.getRandomValues(new Uint32Array(1))[0] % s.length];
  const c = [];
  for (let i = 0; i < 4; i++) c.push(rnd(U));
  for (let i = 0; i < n - 10; i++) c.push(rnd(L));
  for (let i = 0; i < 4; i++) c.push(rnd(D));
  for (let i = 0; i < 2; i++) c.push(rnd(S));
  for (let i = c.length - 1; i > 0; i--) { const k = crypto.getRandomValues(new Uint32Array(1))[0] % (i + 1); [c[i], c[k]] = [c[k], c[i]]; }
  return c.join("");
}

export function passwordProblems(pw, user = "") {
  const e = [];
  if (pw.length < 12) e.push("12+ chars");
  if ((pw.match(/[0-9]/g) || []).length < 2) e.push("2 digits");
  if ((pw.match(/[A-Z]/g) || []).length < 2) e.push("2 uppercase");
  if ((pw.match(/[a-z]/g) || []).length < 2) e.push("2 lowercase");
  if (!/[!@#$%^&*()\-_=+\[\]{}|;:,.<>?/~`]/.test(pw)) e.push("1 symbol");
  if (user && pw.toLowerCase().includes(user.toLowerCase())) e.push("must not contain username");
  if (pw.includes('"')) e.push("no double quote");
  return e;
}

export function cleanHost(h) {
  return String(h || "").trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
}
