#!/usr/bin/env python3
"""SABIGOZAR one-command deploy  ·  Railway + Cloudflare  ·  @SAHEBKARAMI

Does everything the manual guide does, through the official APIs, and is safe to run again
(idempotent): an existing project / service / volume / domain / DNS record is reused, not duplicated.

  1. Railway: project, service from your GitHub repo, volume on /var/lib/sabigozar,
     service settings (healthcheck /healthz, restart ALWAYS, Dockerfile), region,
     Railway domain (port 8080), TCP Proxy (port 8443 = Reality), variables
  2. Railway: custom domain (e.g. panel.example.com)
  3. Cloudflare: proxied CNAME (orange cloud) + _railway-verify TXT, SSL/TLS = Full,
     WebSockets = On, optional removal of stale records (--delete-dns)
  4. Redeploy, wait for SUCCESS and for the domain certificate
  5. End-to-end check: /healthz through Cloudflare, owner login, temporary user from the
     test template, subscription download (every config), temporary user removed again

Why service settings are set here: Railway does not apply railway.json to new services any more
(Config as Code is deprecated), so health check and restart policy are set through the API.

Tokens come from the environment only (never as arguments, never commit them):
  RAILWAY_TOKEN          Railway account/workspace token (railway.com/account/tokens)
  CLOUDFLARE_API_TOKEN   Cloudflare token: Zone:Read, DNS:Edit, Zone Settings:Edit

Example:
  export RAILWAY_TOKEN=...  CLOUDFLARE_API_TOKEN=...
  python3 tools/deploy.py --repo YOUR_USER/SABIGOZAR --domain panel.example.com \\
      --clean-ips 104.16.1.1,172.67.1.1

Only the Python standard library is used.
"""
import argparse, base64, json, os, sys, time, urllib.error, urllib.parse, urllib.request

RAILWAY_API = os.getenv("RAILWAY_API", "https://backboard.railway.app/graphql/v2")
CF_API = "https://api.cloudflare.com/client/v4"
MOUNT_PATH = "/var/lib/sabigozar"
HTTP_PORT, REALITY_PORT = 8080, 8443
DEFAULT_REGION = "europe-west4-drams3a"
TERMINAL = ("SUCCESS", "FAILED", "CRASHED", "REMOVED")
# applied one by one: Railway rejects the whole update if a single field is not accepted
SERVICE_SETTINGS = [{"healthcheckPath": "/healthz"}, {"healthcheckTimeout": 300},
                    {"restartPolicyType": "ALWAYS"}, {"dockerfilePath": "Dockerfile"}]


def log(*a):
    print("[deploy]", *a, flush=True)


def die(msg):
    print(f"[deploy] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def http(method, url, body=None, headers=None, form=False, timeout=60):
    h = {"Accept": "application/json", "User-Agent": "sabigozar-deploy"}
    h.update(headers or {})
    data = None
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode(); h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code, raw, hdrs = r.status, r.read().decode(errors="ignore"), dict(r.headers)
    except urllib.error.HTTPError as e:
        code, raw, hdrs = e.code, e.read().decode(errors="ignore"), dict(e.headers or {})
    except Exception as e:
        return 0, str(e), {}
    try:
        return code, (json.loads(raw) if raw.strip() else None), hdrs
    except ValueError:
        return code, raw, hdrs


# ───────────────────────────── Railway ─────────────────────────────
class Railway:
    def __init__(self, token):
        self.h = {"Authorization": f"Bearer {token}"}

    def q(self, query, variables=None, soft=False):
        code, res, _ = http("POST", RAILWAY_API, {"query": query, "variables": variables or {}}, self.h)
        if not isinstance(res, dict):
            die(f"Railway API {code}: {str(res)[:300]}")
        errs = res.get("errors")
        if errs and not soft:
            die("Railway: " + "; ".join(e.get("message", "?") for e in errs))
        return res.get("data") or {}, errs


def edges(x):
    return [e["node"] for e in ((x or {}).get("edges") or [])]


DOMAINS_Q = """query($p:String!,$e:String!,$s:String!){ domains(projectId:$p, environmentId:$e, serviceId:$s){
  serviceDomains { domain targetPort }
  customDomains { id domain status { verified certificateStatus verificationDnsHost verificationToken
                  dnsRecords { recordType hostlabel fqdn requiredValue status } } } } }"""


def railway_setup(rw, a):
    me, _ = rw.q("query{ me { email workspaces { id name } } }")
    wss = me["me"]["workspaces"]
    if not wss:
        die("no Railway workspace found for this token")
    ws = next((w for w in wss if a.workspace in (w["id"], w["name"])), None) if a.workspace else wss[0]
    if not ws:
        die(f"workspace {a.workspace!r} not found: {[w['name'] for w in wss]}")
    log(f"Railway workspace: {ws['name']}")

    # projects must be listed per workspace: without workspaceId Railway returns only personal ones
    d, _ = rw.q("""query($w:String){ projects(workspaceId:$w) { edges { node { id name
                    environments { edges { node { id name } } }
                    services { edges { node { id name } } } } } } }""", {"w": ws["id"]})
    proj = next((p for p in edges(d.get("projects")) if p["name"] == a.project), None)
    if proj:
        log(f"project {a.project}: exists")
    else:
        d, _ = rw.q("mutation($i: ProjectCreateInput!){ projectCreate(input:$i){ id name "
                    "environments { edges { node { id name } } } services { edges { node { id name } } } } }",
                    {"i": {"name": a.project, "workspaceId": ws["id"]}})
        proj = d["projectCreate"]; log(f"project {a.project}: created")
    pid = proj["id"]
    envs = edges(proj["environments"])
    eid = next((e for e in envs if e["name"] == "production"), envs[0])["id"]

    variables = {"PUBLIC_DOMAIN": a.domain, "PORT": str(HTTP_PORT)}
    if a.clean_ips:
        variables["CLEAN_IPS"] = a.clean_ips
    for kv in a.var or []:
        k, _, v = kv.partition("=")
        variables[k.strip()] = v

    svc = next((s for s in edges(proj["services"]) if s["name"] == a.service), None)
    if svc:
        sid = svc["id"]; log(f"service {a.service}: exists")
        for k, v in variables.items():
            rw.q("mutation($i: VariableUpsertInput!){ variableUpsert(input:$i) }",
                 {"i": {"projectId": pid, "environmentId": eid, "serviceId": sid, "name": k, "value": v, "skipDeploys": True}})
    else:
        d, _ = rw.q("mutation($i: ServiceCreateInput!){ serviceCreate(input:$i){ id } }",
                    {"i": {"projectId": pid, "name": a.service, "source": {"repo": a.repo}, "variables": variables}})
        sid = d["serviceCreate"]["id"]; log(f"service {a.service}: created from github.com/{a.repo}")
    log("variables: " + ", ".join(sorted(variables)))

    d, _ = rw.q("query($p:String!){ project(id:$p){ volumes { edges { node { id volumeInstances { edges { node { mountPath serviceId region } } } } } } } }", {"p": pid})
    vols = [vi for v in edges(d["project"]["volumes"]) for vi in edges(v["volumeInstances"])]
    if any(v["mountPath"] == MOUNT_PATH and v.get("serviceId") in (sid, None) for v in vols):
        log(f"volume {MOUNT_PATH}: exists")
    else:
        rw.q("mutation($i: VolumeCreateInput!){ volumeCreate(input:$i){ id } }",
             {"i": {"projectId": pid, "serviceId": sid, "environmentId": eid, "mountPath": MOUNT_PATH}})
        log(f"volume {MOUNT_PATH}: created")

    upd = f'mutation($i: ServiceInstanceUpdateInput!){{ serviceInstanceUpdate(environmentId:"{eid}", serviceId:"{sid}", input:$i) }}'
    for s in SERVICE_SETTINGS:
        _, errs = rw.q(upd, {"i": s}, soft=True)
        if errs:
            log(f"WARNING: could not set {list(s)[0]}: {errs[0].get('message')}")
    log("service settings: healthcheck /healthz (300s), restart ALWAYS, Dockerfile")
    if a.region:
        rw.q(upd, {"i": {"multiRegionConfig": {a.region: {"numReplicas": 1}}}})
        log(f"region: {a.region}")

    ids = {"p": pid, "e": eid, "s": sid}
    d, _ = rw.q(DOMAINS_Q, ids)
    if d["domains"]["serviceDomains"]:
        log(f"railway domain: {d['domains']['serviceDomains'][0]['domain']}")
    else:
        d2, _ = rw.q("mutation($i: ServiceDomainCreateInput!){ serviceDomainCreate(input:$i){ domain } }",
                     {"i": {"environmentId": eid, "serviceId": sid, "targetPort": HTTP_PORT}})
        log(f"railway domain: {d2['serviceDomainCreate']['domain']} (created)")

    d2, _ = rw.q("query($e:String!,$s:String!){ tcpProxies(environmentId:$e, serviceId:$s){ domain proxyPort applicationPort } }", {"e": eid, "s": sid})
    tcps = d2.get("tcpProxies") or []
    if tcps:
        t = tcps[0]
        if t["applicationPort"] != REALITY_PORT:
            log(f"WARNING: TCP Proxy targets port {t['applicationPort']}, Reality needs {REALITY_PORT}")
    else:
        d3, _ = rw.q("mutation($i: TCPProxyCreateInput!){ tcpProxyCreate(input:$i){ domain proxyPort applicationPort } }",
                     {"i": {"environmentId": eid, "serviceId": sid, "applicationPort": REALITY_PORT}})
        t = d3["tcpProxyCreate"]
    tcp = f"{t['domain'].rstrip('.')}:{t['proxyPort']}"
    log(f"TCP Proxy (Reality): {tcp}")

    cd = next((c for c in d["domains"]["customDomains"] if c["domain"] == a.domain), None)
    if cd:
        log(f"custom domain {a.domain}: exists")
    else:
        av, _ = rw.q("query($d:String!){ customDomainAvailable(domain:$d){ available message } }", {"d": a.domain})
        if not av["customDomainAvailable"]["available"]:
            die(f"{a.domain} is not available on Railway: it is still attached to another Railway project "
                "(an old project or another account). Remove it there, or use another subdomain.")
        d3, _ = rw.q("mutation($i: CustomDomainCreateInput!){ customDomainCreate(input:$i){ id domain status { verified "
                     "certificateStatus verificationDnsHost verificationToken dnsRecords { recordType hostlabel fqdn requiredValue status } } } }",
                     {"i": {"projectId": pid, "environmentId": eid, "serviceId": sid, "domain": a.domain, "targetPort": HTTP_PORT}})
        cd = d3["customDomainCreate"]; log(f"custom domain {a.domain}: added")
    return {"pid": pid, "eid": eid, "sid": sid, "tcp": tcp, "custom": cd}


# ──────────────────────────── Cloudflare ───────────────────────────
class Cloudflare:
    def __init__(self, token):
        self.h = {"Authorization": f"Bearer {token}"}

    def call(self, method, path, body=None):
        code, res, _ = http(method, CF_API + path, body, self.h)
        if not isinstance(res, dict) or not res.get("success"):
            die(f"Cloudflare {method} {path.split('?')[0]} -> {code}: {str(res)[:300]}")
        return res["result"]

    def records(self, zid, name):
        return self.call("GET", f"/zones/{zid}/dns_records?per_page=100&name={urllib.parse.quote(name)}")

    def zone_for(self, host):
        parts = host.split(".")
        for i in range(len(parts) - 1):
            z = self.call("GET", "/zones?name=" + ".".join(parts[i:]))
            if z:
                return z[0]
        die(f"no Cloudflare zone for {host} (is the domain added to this Cloudflare account?)")

    def upsert(self, zid, rtype, name, content, proxied=None, comment=None):
        recs = self.records(zid, name)
        if rtype == "CNAME":  # a CNAME cannot live next to A/AAAA/other CNAME records of the same name
            for r in recs:
                if r["type"] in ("A", "AAAA") or (r["type"] == "CNAME" and r["content"] != content):
                    self.call("DELETE", f"/zones/{zid}/dns_records/{r['id']}")
                    log(f"cloudflare: removed old {r['type']} {name} -> {r['content']}")
        same = [r for r in recs if r["type"] == rtype and r["content"].strip('"') == content.strip('"')]
        if same:
            r = same[0]
            if proxied is not None and r.get("proxied") != proxied:
                self.call("PATCH", f"/zones/{zid}/dns_records/{r['id']}", {"proxied": proxied})
                log(f"cloudflare: {rtype} {name} proxied={proxied}")
            else:
                log(f"cloudflare: {rtype} {name}: ok")
            return
        body = {"type": rtype, "name": name, "content": content, "ttl": 1}
        if proxied is not None:
            body["proxied"] = proxied
        if comment:
            body["comment"] = comment
        self.call("POST", f"/zones/{zid}/dns_records", body)
        log(f"cloudflare: {rtype} {name} -> {content[:48]}" + (" (proxied)" if proxied else ""))

    def setting(self, zid, key, good, want):
        cur = self.call("GET", f"/zones/{zid}/settings/{key}")["value"]
        if cur in good:
            log(f"cloudflare: {key} = {cur}: ok"); return
        self.call("PATCH", f"/zones/{zid}/settings/{key}", {"value": want})
        log(f"cloudflare: {key} {cur} -> {want}")


def cloudflare_setup(cf, a, custom):
    st = custom["status"]
    zone = cf.zone_for(a.domain)
    zid = zone["id"]
    log(f"cloudflare zone: {zone['name']} ({zone['status']})")
    target = next((r["requiredValue"] for r in st["dnsRecords"] if r["recordType"].endswith("CNAME")), None)
    if not target:
        die(f"Railway returned no CNAME target for {a.domain}: {st['dnsRecords']}")
    cf.upsert(zid, "CNAME", a.domain, target, proxied=not a.dns_only, comment="SABIGOZAR panel on Railway")
    if st.get("verificationDnsHost") and st.get("verificationToken"):
        host = st["verificationDnsHost"]
        fq = host if host.endswith(zone["name"]) else f"{host}.{zone['name']}"
        cf.upsert(zid, "TXT", fq, st["verificationToken"])
    # Railway serves HTTPS itself -> Full (Flexible breaks it). WS / HTTPUpgrade / XHTTP need WebSockets.
    cf.setting(zid, "ssl", ("full", "strict"), "full")
    cf.setting(zid, "websockets", ("on",), "on")
    for name in a.delete_dns or []:
        for r in cf.records(zid, name):
            cf.call("DELETE", f"/zones/{zid}/dns_records/{r['id']}")
            log(f"cloudflare: deleted {r['type']} {r['name']} -> {r['content']}")


# ───────────────────────── deploy & verify ─────────────────────────
def latest_deploy(rw, sid):
    d, _ = rw.q(f'query{{ deployments(first:1, input:{{serviceId:"{sid}"}}){{ edges {{ node {{ id status }} }} }} }}')
    n = edges(d["deployments"])
    return n[0] if n else None


def deploy_and_wait(rw, r, redeploy, timeout=1500):
    if redeploy:
        rw.q(f'mutation{{ serviceInstanceRedeploy(environmentId:"{r["eid"]}", serviceId:"{r["sid"]}") }}')
        log("redeploy started"); time.sleep(10)
    t0, last = time.time(), None
    while time.time() - t0 < timeout:
        dep = latest_deploy(rw, r["sid"])
        if dep and dep["status"] != last:
            log(f"deployment {dep['id'][:8]}: {dep['status']}"); last = dep["status"]
        if dep and dep["status"] in TERMINAL:
            if dep["status"] != "SUCCESS":
                die(f"deployment {dep['status']}: open Railway > Deployments > View Logs")
            return dep
        time.sleep(10)
    die("deployment did not finish in time")


def wait_domain(rw, r, domain, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d, _ = rw.q(DOMAINS_Q, {"p": r["pid"], "e": r["eid"], "s": r["sid"]})
        c = next((c for c in d["domains"]["customDomains"] if c["domain"] == domain), None)
        if c and c["status"]["verified"] and "VALID" in (c["status"]["certificateStatus"] or ""):
            log(f"{domain}: verified, certificate valid"); return True
        time.sleep(15)
    log(f"WARNING: {domain} not verified yet (DNS can take a few minutes); run this script again later")
    return False


def read_banner(rw, dep_id):
    d, _ = rw.q(f'query{{ deploymentLogs(deploymentId:"{dep_id}", limit:1000){{ message }} }}', soft=True)
    lines = [x["message"] for x in (d.get("deploymentLogs") or [])]
    info = {"configs": next((l for l in reversed(lines) if "configs ready" in l), None)}
    for l in lines:
        for key in ("Username", "Password"):
            if l.strip().startswith(key) and ":" in l:
                info[key.lower()] = l.split(":", 1)[1].strip()
    return info


def count_links(text):
    t = (text or "").strip()
    try:
        t = base64.b64decode(t + "=" * (-len(t) % 4)).decode()
    except Exception:
        pass
    return [l for l in t.splitlines() if "://" in l]


def remark(link):
    if link.startswith("vmess://"):
        try:
            b = link[8:]
            return json.loads(base64.b64decode(b + "=" * (-len(b) % 4)).decode()).get("ps", "vmess")
        except Exception:
            return "vmess"
    return urllib.parse.unquote(link.split("#", 1)[1]) if "#" in link else link.split("://")[0]


def verify(a, info):
    base = f"https://{a.domain}"
    code, _, hdrs = http("GET", base + "/healthz")
    via = hdrs.get("Server") or hdrs.get("server") or "?"
    log(f"healthz: {code} (served by {via})")
    if code != 200:
        log("WARNING: panel not reachable on the custom domain yet"); return False
    user = info.get("username") or "sabigozar"
    pw = os.getenv("ADMIN_PASSWORD") or info.get("password") or ""
    if not pw or pw.startswith("("):
        log("password hidden in logs: export ADMIN_PASSWORD to run the login test"); return True
    code, res, _ = http("POST", base + "/api/admin/token", {"username": user, "password": pw}, form=True)
    tok = res.get("access_token") if isinstance(res, dict) else None
    log(f"owner login: {'ok' if tok else f'FAILED ({code})'}")
    if not tok:
        return False
    H = {"Authorization": f"Bearer {tok}"}
    name = a.test_user or f"deploycheck{int(time.time()) % 100000}"
    _, tl, _ = http("GET", base + "/api/user_templates", headers=H)
    if isinstance(tl, dict):
        tl = tl.get("user_templates") or []
    tl = tl if isinstance(tl, list) else []
    test = next((t for t in tl if "تست" in t.get("name", "") or "test" in t.get("name", "").lower()), None)
    if test:
        code, res, _ = http("POST", base + "/api/user/from_template", {"user_template_id": test["id"], "username": name}, H)
    else:
        code, res, _ = http("POST", base + "/api/user", {"username": name, "data_limit": 1 << 30, "status": "active",
                                                      "expire": int(time.time()) + 86400, "proxy_settings": {}}, H)
    if code not in (200, 201):
        log(f"test user: FAILED ({code}: {str(res)[:200]})"); return False
    sub, links = None, []
    for _ in range(12):  # the watcher attaches every config to group-less users
        _, u, _ = http("GET", base + f"/api/user/{name}", headers=H)
        sub = u.get("subscription_url") if isinstance(u, dict) else None
        if sub:
            sub = base + sub if sub.startswith("/") else sub
            _, body, _ = http("GET", sub, headers={"User-Agent": "v2rayNG/1.8.5", "Accept": "*/*"})
            links = count_links(body if isinstance(body, str) else "")
            if links:
                break
        time.sleep(5)
    log(f"subscription: {len(links)} configs")
    for l in links:
        log("   " + remark(l))
    if a.test_user:
        log(f"test user {name} kept. subscription link (treat it like a password): {sub}")
    else:
        http("DELETE", base + f"/api/user/{name}", headers=H)
        log(f"temporary user {name} removed")
    return bool(links)


def main():
    p = argparse.ArgumentParser(description="Deploy SABIGOZAR on Railway behind Cloudflare")
    p.add_argument("--repo", required=True, help="GitHub repo, e.g. you/SABIGOZAR (Railway GitHub App needs access)")
    p.add_argument("--domain", required=True, help="panel hostname, e.g. panel.example.com (zone must be on Cloudflare)")
    p.add_argument("--project", default="SABIGOZAR")
    p.add_argument("--service", default="sabigozar")
    p.add_argument("--workspace", help="Railway workspace name or id (default: first)")
    p.add_argument("--region", default=DEFAULT_REGION, help=f"Railway region (default {DEFAULT_REGION}, EU West); '' to keep")
    p.add_argument("--clean-ips", default="", help="comma separated Cloudflare IPs for the CDN configs")
    p.add_argument("--var", action="append", help="extra variable KEY=VALUE (repeatable)")
    p.add_argument("--delete-dns", action="append", help="delete every DNS record of this name (repeatable), e.g. a stale vpn.example.com")
    p.add_argument("--dns-only", action="store_true", help="grey cloud instead of Cloudflare proxy")
    p.add_argument("--no-redeploy", action="store_true", help="do not redeploy (only create / check)")
    p.add_argument("--test-user", help="create (and keep) this test user from the test template and print its subscription link")
    p.add_argument("--skip-verify", action="store_true")
    a = p.parse_args()
    a.domain = a.domain.strip().lower().replace("https://", "").replace("http://", "").strip("/")

    rt, ct = os.getenv("RAILWAY_TOKEN"), os.getenv("CLOUDFLARE_API_TOKEN")
    if not rt or not ct:
        die("set RAILWAY_TOKEN and CLOUDFLARE_API_TOKEN in the environment first")
    rw, cf = Railway(rt), Cloudflare(ct)

    r = railway_setup(rw, a)
    cloudflare_setup(cf, a, r["custom"])
    dep = deploy_and_wait(rw, r, redeploy=not a.no_redeploy)
    wait_domain(rw, r, a.domain)
    info = read_banner(rw, dep["id"])
    if info.get("configs"):
        log(info["configs"].replace("[SABIGOZAR] ", ""))
    ok = True if a.skip_verify else verify(a, info)
    print("\n╔════════════════════ SABIGOZAR deployed ════════════════════╗", flush=True)
    print(f"  Panel    : https://{a.domain}/dashboard/")
    print(f"  Username : {info.get('username') or 'sabigozar'}")
    print("  Password : Railway > Deployments > latest > View Logs (or ADMIN_PASSWORD)")
    print(f"  Reality  : {r['tcp']}")
    print(f"  Check    : {'passed' if ok else 'see warnings above'}")
    print("╚" + "═" * 61 + "╝")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
