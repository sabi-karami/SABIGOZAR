#!/usr/bin/env python3
"""SABIGOZAR end-to-end test  ·  @SAHEBKARAMI
Runs the real image: panel + Xray + nginx, then checks security, rebrand, configs, real traffic
through every protocol (via nginx and via Reality), auto-attach, backups, restart and recovery.
Usage: python3 tests/e2e.py <image>"""
import base64, json, shlex, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

IMG = sys.argv[1] if len(sys.argv) > 1 else "sabigozar:test"
NAME, VOL, BASE = "sabi-e2e", "sabi-e2e-data", "http://127.0.0.1:18080"
FAILS = []


def sh(cmd, inp=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, input=inp)
    return (r.stdout + r.stderr).strip()


def ok(name, cond, extra=""):
    print(("✅ PASS " if cond else "❌ FAIL ") + name + (f"  [{extra}]" if extra != "" else ""), flush=True)
    if not cond:
        FAILS.append(name)


def dx(cmd, inp=None):
    return sh(f"docker exec -i {NAME} sh -c {shlex.quote(cmd)}", inp)


def run(extra=None):
    sh(f"docker rm -f {NAME}")
    env = {"PUBLIC_DOMAIN": "sabi-ci.example.com", "RAILWAY_TCP_PROXY_DOMAIN": "127.0.0.1",
           "RAILWAY_TCP_PROXY_PORT": "8443", "WATCH_SECONDS": "3", "BACKUP_FIRST_DELAY": "5", **(extra or {})}
    e = " ".join(f"-e {k}={shlex.quote(v)}" for k, v in env.items())
    print("container:", sh(f"docker run -d --name {NAME} -p 18080:8080 -v {VOL}:/var/lib/sabigozar {e} {IMG}")[:20])


def logs():
    return sh(f"docker logs {NAME}")


def wait_ready(n=1, t=300):
    t0 = time.time()
    while time.time() - t0 < t:
        if logs().count("watcher on") >= n:
            return round(time.time() - t0)
        time.sleep(3)
    return None


def http(method, path, body=None, tok=None, form=False, accept="application/json"):
    h = {"Accept": accept}
    d = None
    if body is not None:
        d = (urllib.parse.urlencode(body) if form else json.dumps(body)).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
    if tok:
        h["Authorization"] = "Bearer " + tok
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path, data=d, method=method, headers=h), timeout=30) as r:
            raw = r.read().decode(errors="ignore")
            try:
                return r.status, json.loads(raw)
            except ValueError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="ignore")
    except Exception as e:
        return 0, str(e)


def items(res, key):
    return res.get(key, []) if isinstance(res, dict) else (res if isinstance(res, list) else [])


def login(user, pw):
    c, r = http("POST", "/api/admin/token", {"username": user, "password": pw}, form=True)
    return c, (r.get("access_token") if isinstance(r, dict) else None)


def outbound(i, link):
    scheme = link.split("://", 1)[0]
    if scheme == "vmess":
        j = json.loads(base64.b64decode(link[8:] + "==").decode())
        q = {"type": j.get("net"), "path": j.get("path"), "host": j.get("host")}
        user, remark = j["id"], j.get("ps", "")
    else:
        u = urllib.parse.urlsplit(link)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        user, remark = urllib.parse.unquote(u.username or ""), urllib.parse.unquote(u.fragment)
    net = q.get("type") or "tcp"
    if q.get("security") == "reality":
        stream = {"network": "tcp", "security": "reality", "realitySettings": {
            "serverName": q.get("sni"), "fingerprint": q.get("fp", "chrome"), "publicKey": q.get("pbk"), "shortId": q.get("sid", "")}}
        addr, port = "127.0.0.1", 8443
    else:
        stream = {"network": net, "security": "none"}
        key = {"ws": "wsSettings", "httpupgrade": "httpupgradeSettings", "xhttp": "xhttpSettings"}[net]
        stream[key] = {"path": q.get("path"), "host": q.get("host")}
        if net == "xhttp":
            stream[key]["mode"] = q.get("mode", "packet-up")
        addr, port = "127.0.0.1", 8080
    if scheme == "trojan":
        st = {"servers": [{"address": addr, "port": port, "password": user}]}
    elif scheme == "vmess":
        st = {"vnext": [{"address": addr, "port": port, "users": [{"id": user, "security": "auto"}]}]}
    else:
        st = {"vnext": [{"address": addr, "port": port, "users": [{"id": user, "encryption": "none", "flow": q.get("flow", "")}]}]}
    return remark, {"tag": f"o{i}", "protocol": scheme, "settings": st, "streamSettings": stream}


def main():
    sh(f"docker rm -f {NAME}; docker volume rm {VOL}")
    run()
    secs = wait_ready()
    ok("boots and finishes setup", secs is not None, f"{secs}s")
    L = logs()
    ok("no FATAL in setup log", "FATAL" not in L)
    ok("credentials banner printed", "SABIGOZAR" in L and "Username" in L)

    st = json.loads(dx("cat /var/lib/sabigozar/owner.json") or "{}")
    ok("owner credentials stored", bool(st.get("password")), st.get("username"))
    ok("owner file is private (600)", dx("stat -c %a /var/lib/sabigozar/owner.json") == "600")
    c, TOK = login(st.get("username"), st.get("password"))
    ok("owner login works", c == 200)
    ok("admin/admin is rejected", login("admin", "admin")[0] == 401)
    ok("reseller/reseller does not exist", login("reseller", "reseller")[0] == 401)

    ok("/healthz", http("GET", "/healthz")[0] == 200)
    c, page = http("GET", "/dashboard/", accept="text/html")
    ok("dashboard is branded SABIGOZAR", c == 200 and "<title>SABIGOZAR</title>" in str(page))
    ok("PasarGuard ad feed removed", dx("grep -rl 'pasarguard/ads' /code/dashboard/build || echo none") == "none")
    ok("local QR library served", http("GET", "/__sabigozar/static/qrcode.js")[0] == 200)
    ok("nginx config valid", "successful" in dx("nginx -t 2>&1"))

    c, nodes = http("GET", "/api/nodes", tok=TOK)
    ok("Xray node connected", any(n.get("status") == "connected" for n in items(nodes, "nodes")))
    c, hosts = http("GET", "/api/hosts", tok=TOK)
    remarks = [h["remark"] for h in items(hosts, "hosts")]
    ok("8 hosts (Reality + 6 + Fragment)", len(remarks) == 8, len(remarks))
    c, tpls = http("GET", "/api/user_templates", tok=TOK)
    ok("8 sale templates", len(items(tpls, "templates")) >= 8, len(items(tpls, "templates")))
    c, roles = http("GET", "/api/admin-roles", tok=TOK)
    ok("reseller role exists", any("SABIGOZAR" in r.get("name", "") for r in items(roles, "roles")))
    c, groups = http("GET", "/api/groups", tok=TOK)
    gid = [g["id"] for g in items(groups, "groups") if g["name"] == "sabigozar-all"][0]

    c, u = http("POST", "/api/user", {"username": "ci_user", "group_ids": [gid], "status": "active",
                                        "data_limit": 10 * 1024 ** 3, "expire": int(time.time()) + 30 * 86400,
                                        "data_limit_reset_strategy": "no_reset"}, tok=TOK)
    ok("create user", c in (200, 201), c)
    tk = u["subscription_url"].rstrip("/").split("/")[-1]
    c, raw = http("GET", f"/sub/{tk}/links")
    links = [l for l in str(raw).splitlines() if "://" in l]
    ok("subscription returns 8 configs", len(links) == 8, len(links))
    rl = [l for l in links if "security=reality" in l]
    ok("Reality link has pbk/sid/vision", bool(rl) and all(k in rl[0] for k in ("pbk=", "sid=", "flow=xtls-rprx-vision")))
    c, html = http("GET", f"/sub/{tk}", accept="text/html")
    ok("SABIGOZAR subscription page", c == 200 and "SABIGOZAR" in str(html) and "SAHEBKARAMI" in str(html))

    cfg = {"log": {"loglevel": "warning"}, "inbounds": [], "outbounds": [], "routing": {"rules": []}}
    names = []
    for i, l in enumerate(links):
        remark, ob = outbound(i, l)
        names.append(remark)
        cfg["inbounds"].append({"tag": f"i{i}", "listen": "127.0.0.1", "port": 31000 + i, "protocol": "socks", "settings": {"udp": False}})
        cfg["outbounds"].append(ob)
        cfg["routing"]["rules"].append({"type": "field", "inboundTag": [f"i{i}"], "outboundTag": f"o{i}"})
    dx("cat > /tmp/client.json", json.dumps(cfg))
    sh(f"docker exec -d {NAME} /usr/local/bin/xray run -config /tmp/client.json")
    time.sleep(4)
    for i, n in enumerate(names):
        r = dx(f"curl -s -o /dev/null --max-time 20 -w '%{{http_code}} %{{time_total}}' --socks5-hostname 127.0.0.1:{31000 + i} https://www.gstatic.com/generate_204")
        ok(f"traffic · {n}", r.startswith("204"), r)

    http("POST", "/api/user", {"username": "ci_orphan", "status": "active", "data_limit": 0,
                               "data_limit_reset_strategy": "no_reset"}, tok=TOK)
    got = None
    for _ in range(15):
        time.sleep(2)
        got = http("GET", "/api/user/ci_orphan", tok=TOK)[1]
        if isinstance(got, dict) and got.get("group_ids"):
            break
    ok("user without group gets every config", isinstance(got, dict) and bool(got.get("group_ids")))
    time.sleep(6)
    ok("automatic DB backup created", "sabigozar-" in dx("ls /var/lib/sabigozar/backups"))

    sh(f"docker restart {NAME}")
    ok("restart: setup finishes again", wait_ready(2) is not None)
    c, TOK2 = login(st["username"], st["password"])
    ok("restart: same password still works", c == 200)
    ok("restart: no duplicate hosts", len(items(http("GET", "/api/hosts", tok=TOK2)[1], "hosts")) == 8)
    ok("restart: one core", len(items(http("GET", "/api/cores", tok=TOK2)[1], "cores")) == 1)
    ok("restart: users kept", http("GET", "/api/user/ci_user", tok=TOK2)[0] == 200)

    NEW = "Sahe8Karami!!Gz42"
    run({"ADMIN_PASSWORD": NEW})
    ok("recovery: setup finishes", wait_ready() is not None)
    ok("recovery: ADMIN_PASSWORD works", login(st["username"], NEW)[0] == 200)
    ok("recovery: old password rejected", login(st["username"], st["password"])[0] == 401)
    run({"ADMIN_PASSWORD": "admin"})
    wait_ready()
    ok("weak ADMIN_PASSWORD refused", "ADMIN_PASSWORD ignored" in logs())
    ok("weak: previous password kept", login(st["username"], NEW)[0] == 200)

    print("\n" + ("🎉 ALL TESTS PASSED" if not FAILS else f"💥 {len(FAILS)} FAILED: {FAILS}"))
    if not FAILS:
        sh(f"docker rm -f {NAME}; docker volume rm {VOL}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
