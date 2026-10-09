// SABIGOZAR Deploy Panel · Cloudflare Worker · @SAHEBKARAMI
// GET /            -> panel page
// POST /api/<step> -> one deploy step (header x-panel-key = PANEL_PASSWORD secret)
// Tokens arrive per request and are never stored or logged.
import { STEPS } from "./steps.js";
import HTML from "./ui.js";
import APP from "./app.js";

const SEC = { "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow" };
const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "Content-Type": "application/json; charset=utf-8", ...SEC } });

function same(a, b) {
  a = String(a || ""); b = String(b || "");
  if (!a || !b) return false;
  let x = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) x |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return x === 0;
}

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    if (req.method === "GET" && (u.pathname === "/" || u.pathname === "/index.html"))
      return new Response(HTML, { headers: { "Content-Type": "text/html; charset=utf-8", ...SEC } });
    if (req.method === "GET" && u.pathname === "/app.js")
      return new Response(APP, { headers: { "Content-Type": "application/javascript; charset=utf-8", ...SEC } });
    if (u.pathname === "/healthz") return new Response("ok\n", { headers: SEC });
    const m = u.pathname.match(/^\/api\/([a-z]+)$/);
    if (!m || req.method !== "POST") return json({ ok: false, error: "not found" }, 404);
    if (!env.PANEL_PASSWORD) return json({ ok: false, error: "PANEL_PASSWORD secret is not set on this Worker" }, 503);
    if (!same(req.headers.get("x-panel-key"), env.PANEL_PASSWORD)) {
      await new Promise((r) => setTimeout(r, 900));
      return json({ ok: false, error: "auth" }, 401);
    }
    if (m[1] === "login") return json({ ok: true });
    const fn = STEPS[m[1]];
    if (!fn) return json({ ok: false, error: "unknown step" }, 404);
    let body;
    try { body = await req.json(); } catch { return json({ ok: false, error: "bad json" }, 400); }
    const logs = [];
    const log = (t, l = "info") => logs.push({ t: String(t), l });
    try {
      const st = await fn(body.inp || {}, body.st || {}, log, env, u.host);
      return json({ ok: true, st: { ...(body.st || {}), ...(st || {}) }, logs });
    } catch (e) {
      log(String((e && e.message) || e), "err");
      return json({ ok: false, error: String((e && e.message) || e), logs });
    }
  },
};
