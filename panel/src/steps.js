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
  for (const [k, v] of [["healthcheckPath", "/healthz"], ["healthcheckTimeout", 300], ["restartPolicyType", "ALWAYS"], ["dockerfilePath", "Dockerfile"], ["builder", "DOCKERFILE"]]) {
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
