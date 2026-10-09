// SABIGOZAR Deploy Panel · every deploy step (one request each) · @SAHEBKARAMI
import { gql, cf, gh, edges, sleep, strongPassword, passwordProblems, cleanHost, StepError, MOUNT, HTTP_PORT, REALITY_PORT } from "./lib.js";

const DOMQ = `query($p:String!,$e:String!,$s:String!){ domains(projectId:$p, environmentId:$e, serviceId:$s){
  serviceDomains { domain targetPort }
  customDomains { id domain status { verified certificateStatus verificationDnsHost verificationToken dnsRecords { recordType hostlabel requiredValue status } } } } }`;
const need = (v, n) => { if (!v) throw new StepError(n + " is required"); return v; };
const ids = (st) => ({ p: st.pid, e: st.eid, s: st.sid });

/* 1 · check every key and input before touching anything */
async function check(inp, st, log) {
  need(inp.railwayToken, "Railway token"); need(inp.cfToken, "Cloudflare token"); need(inp.domain, "Panel domain");
  const domain = cleanHost(inp.domain);
  if (!/^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(domain)) throw new StepError("domain looks wrong: " + domain);
  const me = await gql(inp.railwayToken, "query{ me { email workspaces { id name } } }");
  const ws = me.me.workspaces.find((w) => !inp.workspace || w.name === inp.workspace || w.id === inp.workspace) || me.me.workspaces[0];
  if (!ws) throw new StepError("no Railway workspace for this token");
  log(`Railway ✓ ${me.me.email} · workspace «${ws.name}»`, "ok");
  const parts = domain.split(".");
  let zone = null;
  for (let i = 0; i < parts.length - 1 && !zone; i++) { const z = await cf(inp.cfToken, "GET", "/zones?name=" + parts.slice(i).join(".")); if (z.length) zone = z[0]; }
  if (!zone) throw new StepError("no Cloudflare zone for " + domain + " (is the domain on this Cloudflare account?)");
  log(`Cloudflare ✓ zone ${zone.name} (${zone.status})`, "ok");
  const user = (inp.adminUser || "sabigozar").trim();
  if (inp.adminPass) { const bad = passwordProblems(inp.adminPass, user); if (bad.length) throw new StepError("admin password needs: " + bad.join(", ")); }
  if (inp.ghToken) { const r = await gh(inp.ghToken, "GET", "/user"); if (r.status !== 200) throw new StepError("GitHub token rejected (" + r.status + ")"); log(`GitHub ✓ ${r.j.login}`, "ok"); }
  return { domain, wsId: ws.id, wsName: ws.name, email: me.me.email, zid: zone.id, zone: zone.name, adminUser: user, region: inp.region || "europe-west4-drams3a" };
}

/* 2 · GitHub: fork the source repo or sync an existing fork */
async function github(inp, st, log) {
  const src = (inp.sourceRepo || "sabi-karami/SABIGOZAR").trim();
  let repo = (inp.repo || "").trim();
  if (!inp.ghToken) {
    repo = repo || src;
    log(`No GitHub token: Railway builds from ${repo} as it is (sync your fork on GitHub yourself).`, "warn");
    return { repo };
  }
  const me = (await gh(inp.ghToken, "GET", "/user")).j.login;
  if (!repo) {
    const own = await gh(inp.ghToken, "GET", `/repos/${me}/${src.split("/")[1]}`);
    if (own.status === 200) repo = own.j.full_name;
    else if (src.split("/")[0].toLowerCase() === me.toLowerCase()) repo = src;
    else {
      const f = await gh(inp.ghToken, "POST", `/repos/${src}/forks`, {});
      if (f.status >= 300) throw new StepError("fork failed: " + (f.j.message || f.status));
      repo = f.j.full_name; log(`Forked ${src} → ${repo}`, "ok"); await sleep(5000);
    }
  }
  const info = await gh(inp.ghToken, "GET", `/repos/${repo}`);
  if (info.status !== 200) throw new StepError(`repo ${repo} not found for this token`);
  if (info.j.fork) {
    const s = await gh(inp.ghToken, "POST", `/repos/${repo}/merge-upstream`, { branch: info.j.default_branch });
    if (s.status === 200) log(`Fork synced with upstream: ${s.j.message || "up to date"}`, "ok");
    else log(`Could not sync fork (${s.status}: ${s.j.message || ""}). Press «Sync fork» on GitHub.`, "warn");
  } else log(`Repo ${repo} (not a fork, nothing to sync)`, "ok");
  const head = await gh(inp.ghToken, "GET", `/repos/${repo}/commits/${info.j.default_branch}`);
  return { repo, commit: head.status === 200 ? head.j.sha.slice(0, 7) : "" };
}

/* 3 · Railway project + service + variables (with automatic admin login) */
async function railway(inp, st, log) {
  const T = inp.railwayToken;
  const d = await gql(T, `query($w:String){ projects(workspaceId:$w){ edges { node { id name environments { edges { node { id name } } } services { edges { node { id name } } } } } } }`, { w: st.wsId });
  const name = inp.project || "SABIGOZAR", svcName = inp.service || "sabigozar";
  let proj = edges(d.projects).find((p) => p.name === name);
  if (proj) log(`Project «${name}» exists, reusing it`);
  else {
    const c = await gql(T, `mutation($i: ProjectCreateInput!){ projectCreate(input:$i){ id name environments { edges { node { id name } } } services { edges { node { id name } } } } }`, { i: { name, workspaceId: st.wsId } });
    proj = c.projectCreate; log(`Project «${name}» created`, "ok");
  }
  const envs = edges(proj.environments), env = envs.find((e) => e.name === "production") || envs[0];
  let svc = edges(proj.services).find((s) => s.name === svcName), existing = {};
  if (svc) {
    const v = await gql(T, `query($p:String!,$e:String!,$s:String!){ variables(projectId:$p, environmentId:$e, serviceId:$s) }`, { p: proj.id, e: env.id, s: svc.id }, true);
    existing = (v.data && v.data.variables) || {};
  }
  const vars = { PUBLIC_DOMAIN: st.domain, PORT: String(HTTP_PORT) };
  if (inp.cleanIps) vars.CLEAN_IPS = inp.cleanIps.replace(/\s+/g, "");
  vars.ADMIN_USERNAME = existing.ADMIN_USERNAME || st.adminUser;
  let pwSource = "kept";
  if (inp.adminPass) { vars.ADMIN_PASSWORD = inp.adminPass; pwSource = "yours"; }
  else if (existing.ADMIN_PASSWORD) vars.ADMIN_PASSWORD = existing.ADMIN_PASSWORD;
  else { vars.ADMIN_PASSWORD = strongPassword(); pwSource = "generated"; }
  for (const kv of String(inp.extraVars || "").split("\n")) { const i = kv.indexOf("="); if (i > 0) vars[kv.slice(0, i).trim()] = kv.slice(i + 1).trim(); }
  if (svc) {
    for (const [k, v] of Object.entries(vars)) if (existing[k] !== v)
      await gql(T, `mutation($i: VariableUpsertInput!){ variableUpsert(input:$i) }`, { i: { projectId: proj.id, environmentId: env.id, serviceId: svc.id, name: k, value: v, skipDeploys: true } });
    log(`Service «${svcName}» exists, variables updated`);
  } else {
    const c = await gql(T, `mutation($i: ServiceCreateInput!){ serviceCreate(input:$i){ id } }`, { i: { projectId: proj.id, name: svcName, source: { repo: st.repo }, variables: vars } });
    svc = { id: c.serviceCreate.id }; log(`Service «${svcName}» created from github.com/${st.repo}`, "ok");
  }
  log(`Variables: ${Object.keys(vars).join(", ")}`);
  log(pwSource === "generated" ? "ADMIN_PASSWORD: a strong random password was generated" : pwSource === "yours" ? "ADMIN_PASSWORD: your password was set" : "ADMIN_PASSWORD: existing password kept", "ok");
  return { pid: proj.id, eid: env.id, sid: svc.id, project: name, service: svcName, adminUser: vars.ADMIN_USERNAME, adminPass: vars.ADMIN_PASSWORD, pwSource };
}

/* 4 · volume + service settings + region */
async function settings(inp, st, log) {
  const T = inp.railwayToken;
  const d = await gql(T, `query($p:String!){ project(id:$p){ volumes { edges { node { id name volumeInstances { edges { node { mountPath serviceId region } } } } } } } }`, { p: st.pid });
  const vols = edges(d.project.volumes).flatMap((v) => edges(v.volumeInstances).map((i) => ({ ...i, name: v.name })));
  const have = vols.find((v) => v.mountPath === MOUNT && (!v.serviceId || v.serviceId === st.sid));
  if (have) log(`Volume «${have.name}» on ${MOUNT} exists (${have.region || ""})`);
  else { await gql(T, `mutation($i: VolumeCreateInput!){ volumeCreate(input:$i){ id } }`, { i: { projectId: st.pid, serviceId: st.sid, environmentId: st.eid, mountPath: MOUNT } }); log(`Volume created on ${MOUNT}`, "ok"); }
  const upd = `mutation($i: ServiceInstanceUpdateInput!){ serviceInstanceUpdate(environmentId:"${st.eid}", serviceId:"${st.sid}", input:$i) }`;
  for (const [k, v] of [["healthcheckPath", "/healthz"], ["healthcheckTimeout", 300], ["restartPolicyType", "ALWAYS"], ["dockerfilePath", "Dockerfile"]]) {
    const r = await gql(T, upd, { i: { [k]: v } }, true);
    log(r.errors ? `${k}: not accepted by Railway (${r.errors[0].message})` : `${k} = ${v}`, r.errors ? "warn" : "ok");
  }
  await gql(T, upd, { i: { multiRegionConfig: { [st.region]: { numReplicas: 1 } } } });
  log(`Region = ${st.region}`, "ok");
  return { volume: MOUNT };
}

/* 5 · Railway domain + TCP proxy (Reality) + custom domain */
async function domains(inp, st, log) {
  const T = inp.railwayToken;
  let d = await gql(T, DOMQ, ids(st));
  let rd = d.domains.serviceDomains[0] && d.domains.serviceDomains[0].domain;
  if (rd) log(`Railway domain ${rd} exists`);
  else { const c = await gql(T, `mutation($i: ServiceDomainCreateInput!){ serviceDomainCreate(input:$i){ domain } }`, { i: { environmentId: st.eid, serviceId: st.sid, targetPort: HTTP_PORT } }); rd = c.serviceDomainCreate.domain; log(`Railway domain ${rd} created (port ${HTTP_PORT})`, "ok"); }
  const tq = await gql(T, `query($e:String!,$s:String!){ tcpProxies(environmentId:$e, serviceId:$s){ domain proxyPort applicationPort } }`, { e: st.eid, s: st.sid });
  let t = (tq.tcpProxies || [])[0];
  if (t) { log(`TCP Proxy exists ${t.domain.replace(/\.$/, "")}:${t.proxyPort}`); if (t.applicationPort !== REALITY_PORT) log(`TCP Proxy targets port ${t.applicationPort}; Reality needs ${REALITY_PORT}`, "warn"); }
  else { const c = await gql(T, `mutation($i: TCPProxyCreateInput!){ tcpProxyCreate(input:$i){ domain proxyPort applicationPort } }`, { i: { environmentId: st.eid, serviceId: st.sid, applicationPort: REALITY_PORT } }); t = c.tcpProxyCreate; log(`TCP Proxy created ${t.domain.replace(/\.$/, "")}:${t.proxyPort} → ${REALITY_PORT} (Reality)`, "ok"); }
  let cd = d.domains.customDomains.find((c) => c.domain === st.domain);
  if (cd) log(`Custom domain ${st.domain} exists`);
  else {
    const a = await gql(T, `query($d:String!){ customDomainAvailable(domain:$d){ available message } }`, { d: st.domain });
    if (!a.customDomainAvailable.available) throw new StepError(`${st.domain} is not available on Railway: it is still attached to another Railway project. Remove it there or use another subdomain.`);
    const c = await gql(T, `mutation($i: CustomDomainCreateInput!){ customDomainCreate(input:$i){ id domain status { verified certificateStatus verificationDnsHost verificationToken dnsRecords { recordType hostlabel requiredValue status } } } }`, { i: { projectId: st.pid, environmentId: st.eid, serviceId: st.sid, domain: st.domain, targetPort: HTTP_PORT } });
    cd = c.customDomainCreate; log(`Custom domain ${st.domain} added on Railway`, "ok");
  }
  const target = (cd.status.dnsRecords.find((r) => /CNAME/.test(r.recordType)) || {}).requiredValue;
  if (!target) throw new StepError("Railway returned no CNAME target");
  return { railwayDomain: rd, tcp: `${t.domain.replace(/\.$/, "")}:${t.proxyPort}`, cname: target, txtHost: cd.status.verificationDnsHost || "", txtVal: cd.status.verificationToken || "" };
}

/* 6 · Cloudflare: proxied CNAME + verification TXT + SSL Full + WebSockets + stale records */
async function upsert(T, zid, type, name, content, proxied, log) {
  const recs = await cf(T, "GET", `/zones/${zid}/dns_records?per_page=100&name=${encodeURIComponent(name)}`);
  if (type === "CNAME") for (const r of recs) if (r.type === "A" || r.type === "AAAA" || (r.type === "CNAME" && r.content !== content)) {
    await cf(T, "DELETE", `/zones/${zid}/dns_records/${r.id}`); log(`Removed old ${r.type} ${name} → ${r.content}`, "warn");
  }
  const same = recs.find((r) => r.type === type && r.content.replace(/"/g, "") === content.replace(/"/g, ""));
  if (same) {
    if (proxied !== undefined && same.proxied !== proxied) { await cf(T, "PATCH", `/zones/${zid}/dns_records/${same.id}`, { proxied }); log(`${type} ${name}: proxy = ${proxied}`, "ok"); }
    else log(`${type} ${name} already correct`);
    return;
  }
  const body = { type, name, content, ttl: 1, comment: "SABIGOZAR panel (auto)" };
  if (proxied !== undefined) body.proxied = proxied;
  await cf(T, "POST", `/zones/${zid}/dns_records`, body);
  log(`${type} ${name} → ${content.slice(0, 48)}${proxied ? " (proxied 🟠)" : ""}`, "ok");
}
async function setting(T, zid, key, good, want, log) {
  const cur = (await cf(T, "GET", `/zones/${zid}/settings/${key}`)).value;
  if (good.includes(cur)) { log(`${key} = ${cur} ✓`); return cur; }
  await cf(T, "PATCH", `/zones/${zid}/settings/${key}`, { value: want }); log(`${key}: ${cur} → ${want}`, "ok"); return want;
}
async function cloudflare(inp, st, log) {
  const T = inp.cfToken;
  await upsert(T, st.zid, "CNAME", st.domain, st.cname, !inp.dnsOnly, log);
  if (st.txtHost && st.txtVal) await upsert(T, st.zid, "TXT", st.txtHost.endsWith(st.zone) ? st.txtHost : `${st.txtHost}.${st.zone}`, st.txtVal, undefined, log);
  const ssl = await setting(T, st.zid, "ssl", ["full", "strict"], "full", log);
  const ws = await setting(T, st.zid, "websockets", ["on"], "on", log);
  const deleted = [];
  for (const n of String(inp.deleteDns || "").split(/[\s,]+/).map(cleanHost).filter(Boolean)) {
    if (n === st.domain || n === st.panelHost) { log(`Skipped deleting ${n} (in use)`, "warn"); continue; }
    for (const r of await cf(T, "GET", `/zones/${st.zid}/dns_records?per_page=100&name=${encodeURIComponent(n)}`)) {
      await cf(T, "DELETE", `/zones/${st.zid}/dns_records/${r.id}`); deleted.push(`${r.type} ${r.name}`); log(`Deleted ${r.type} ${r.name} → ${r.content}`, "ok");
    }
  }
  return { ssl, ws, deleted };
}

/* 7 · redeploy with the newest commit */
async function deploy(inp, st, log) {
  const T = inp.railwayToken;
  const r = await gql(T, `mutation{ serviceInstanceDeploy(environmentId:"${st.eid}", serviceId:"${st.sid}", latestCommit:true) }`, {}, true);
  if (r.errors) { await gql(T, `mutation{ serviceInstanceRedeploy(environmentId:"${st.eid}", serviceId:"${st.sid}") }`); log("Redeploy started", "ok"); }
  else log("Deploy of the latest commit started", "ok");
  await sleep(4000);
  return { deployStart: Date.now() };
}

/* 8 · poll until SUCCESS (the page calls this repeatedly) */
async function wait(inp, st, log) {
  const T = inp.railwayToken;
  const d = await gql(T, `query{ deployments(first:1, input:{serviceId:"${st.sid}"}){ edges { node { id status createdAt meta } } } }`);
  const n = edges(d.deployments)[0];
  if (!n) { log("Waiting for Railway to create the deployment…"); return { done: false }; }
  const c = n.meta && n.meta.commitHash ? n.meta.commitHash.slice(0, 7) : "";
  log(`Deployment ${n.id.slice(0, 8)} · ${n.status}${c ? " · commit " + c : ""}`);
  if (["FAILED", "CRASHED"].includes(n.status)) throw new StepError(`Deployment ${n.status}: open Railway → Deployments → View Logs`);
  if (n.status !== "SUCCESS") return { done: false };
  const dq = await gql(T, DOMQ, ids(st));
  const c2 = dq.domains.customDomains.find((x) => x.domain === st.domain);
  const ok = c2 && c2.status.verified && /VALID/.test(c2.status.certificateStatus || "");
  if (!ok) { log(`Deployed. Waiting for ${st.domain} verification + certificate (DNS can take a few minutes)…`); return { done: false, depId: n.id }; }
  const l = await gql(T, `query{ deploymentLogs(deploymentId:"${n.id}", limit:1000){ message } }`, {}, true);
  const lines = ((l.data && l.data.deploymentLogs) || []).map((x) => x.message);
  const cfg = [...lines].reverse().find((x) => /configs ready/.test(x)) || "";
  if (!cfg && Date.now() - (st.deployStart || 0) < 240000) { log("Panel is booting (configs not ready yet)…"); return { done: false, depId: n.id }; }
  if (cfg) log(cfg.replace("[SABIGOZAR] ", ""), "ok");
  log(`${st.domain}: verified, certificate valid`, "ok");
  return { done: true, depId: n.id, deployedCommit: c, configsLine: cfg.replace("[SABIGOZAR] ", "") };
}

/* 9 · end-to-end test through Cloudflare */
async function verify(inp, st, log) {
  const B = `https://${st.domain}`;
  const h = await fetch(B + "/healthz", { cf: { cacheTtl: 0 } });
  log(`healthz ${h.status} · served by ${h.headers.get("server") || "?"}`, h.status === 200 ? "ok" : "err");
  if (h.status !== 200) throw new StepError("panel not reachable on " + st.domain);
  const lr = await fetch(B + "/api/admin/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ username: st.adminUser, password: st.adminPass }) });
  const tok = lr.ok ? (await lr.json()).access_token : null;
  log(tok ? "Owner login ✓" : `Owner login failed (${lr.status})`, tok ? "ok" : "err");
  if (!tok) throw new StepError("owner login failed: check ADMIN_PASSWORD in Railway Variables");
  const H = { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" };
  const tl = await (await fetch(B + "/api/user_templates", { headers: H })).json().catch(() => []);
  const list = Array.isArray(tl) ? tl : tl.user_templates || tl.templates || [];
  log(`Sale templates: ${list.length}`, list.length ? "ok" : "warn");
  const keep = cleanHost(inp.testUser || "").replace(/[^a-z0-9_]/gi, "");
  const name = keep || `paneltest${Date.now() % 100000}`;
  const tpl = list.find((t) => /تست|test/i.test(t.name || ""));
  const cr = tpl
    ? await fetch(B + "/api/user/from_template", { method: "POST", headers: H, body: JSON.stringify({ user_template_id: tpl.id, username: name }) })
    : await fetch(B + "/api/user", { method: "POST", headers: H, body: JSON.stringify({ username: name, data_limit: 1073741824, expire: Math.floor(Date.now() / 1000) + 86400, status: "active", proxy_settings: {} }) });
  if (cr.status >= 300) throw new StepError(`test user failed (${cr.status}): ${(await cr.text()).slice(0, 160)}`);
  log(`Test user «${name}» created${tpl ? " from «" + tpl.name + "»" : ""}`, "ok");
  let sub = "", names = [];
  for (let i = 0; i < 8 && !names.length; i++) {
    await sleep(4000);
    const u = await (await fetch(B + `/api/user/${name}`, { headers: H })).json().catch(() => ({}));
    sub = u.subscription_url ? (u.subscription_url.startsWith("/") ? B + u.subscription_url : u.subscription_url) : "";
    if (!sub) continue;
    const raw = (await (await fetch(sub + "/links", { headers: { "User-Agent": "v2rayNG/1.8.5" } })).text()).trim();
    names = raw.split(/\s+/).filter((l) => l.includes("://")).map((l) => {
      if (l.startsWith("vmess://")) { try { return JSON.parse(atob(l.slice(8))).ps || "vmess"; } catch { return "vmess"; } }
      try { return decodeURIComponent(l.split("#")[1] || l.split("://")[0]); } catch { return l.split("://")[0]; }
    });
  }
  log(`Subscription: ${names.length} configs`, names.length ? "ok" : "err");
  names.forEach((n) => log("   " + n));
  const page = sub ? await fetch(sub, { headers: { Accept: "text/html", "User-Agent": "Mozilla/5.0" } }) : null;
  const pageOk = !!page && page.ok && /SABIGOZAR/.test(await page.text());
  log(pageOk ? "Subscription web page ✓" : "Subscription web page did not load", pageOk ? "ok" : "warn");
  if (!keep) { await fetch(B + `/api/user/${name}`, { method: "DELETE", headers: H }); log(`Temporary user «${name}» removed`); }
  return { configs: names, testUser: keep ? name : "", testSub: keep ? sub : "", pageOk, verified: names.length > 0 };
}

/* 10 · final report */
async function report(inp, st, log) {
  log("Report ready", "ok");
  return { finished: new Date().toISOString() };
}

export const STEPS = { check, github, railway, settings, domains, cloudflare, deploy, wait, verify, report };
export const ORDER = ["check", "github", "railway", "settings", "domains", "cloudflare", "deploy", "wait", "verify", "report"];
