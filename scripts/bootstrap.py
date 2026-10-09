"""SABIGOZAR bootstrap  ·  zero-touch, idempotent setup on every boot  ·  @SAHEBKARAMI

* Owner is created through PasarGuard's official one-time setup key (no DB hacks).
* Password: ADMIN_PASSWORD variable if set (also = password recovery), otherwise a strong
  random one generated once and kept on the volume. Printed in the deploy logs.
* Core, node, group, hosts and subscription settings are (re)applied every boot.
* Watcher: users created without a group automatically receive every config."""
import json, os, secrets, string, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import protocols  # noqa: E402

DATA = os.getenv("SABI_DATA", "/var/lib/sabigozar")
CODE = os.getenv("SABI_CODE_DIR", "/code")
BASE = os.getenv("SABI_PANEL_URL", "http://127.0.0.1:8000")
BRAND, SUPPORT = "SABIGOZAR", "https://t.me/SAHEBKARAMI"
TITLE = os.getenv("CONFIG_TITLE", BRAND)
DOMAIN = (os.getenv("PUBLIC_DOMAIN") or os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip().lower()
DOMAIN = DOMAIN.replace("https://", "").replace("http://", "").strip("/")
STATE = os.path.join(DATA, "owner.json")
HOSTS_STATE = os.path.join(DATA, "hosts.json")
CORE_NAME, NODE_NAME, GROUP_NAME = "SABIGOZAR-Core", "SABIGOZAR-Local", "sabigozar-all"
SPECIAL = "!@#$%^&*-_=+"
TOKEN = None
CTX = {}


def log(*a):
    print("[SABIGOZAR]", *a, flush=True)


def env_bool(k, d=False):
    v = os.getenv(k)
    return d if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def load_secrets():
    s = {}
    try:
        for line in open(os.path.join(DATA, "secrets.env")):
            if "=" in line:
                k, v = line.strip().split("=", 1); s[k] = v
    except FileNotFoundError:
        pass
    return s


def req(method, path, body=None, form=False, auth=True):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode(); headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
    if auth and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, (json.loads(raw) if raw.strip() else None)
            except ValueError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="ignore")
        try:
            return e.code, json.loads(txt)
        except ValueError:
            return e.code, txt


def must(method, path, body=None):
    code, res = req(method, path, body)
    if code == 401 and relogin():
        code, res = req(method, path, body)
    if code not in (200, 201, 204):
        raise RuntimeError(f"{method} {path} -> {code}: {str(res)[:300]}")
    return res


def as_list(res, key):
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        return res.get(key) or []
    return []


def wait_panel():
    for _ in range(240):
        try:
            code, _ = req("GET", "/api/system", auth=False)
            if code in (200, 401, 403):
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("panel did not come up")


def password_problems(pw, username=""):
    e = []
    if len(pw.encode()) > 72: e.append("max 72 bytes")
    if len(pw) < 12: e.append("at least 12 characters")
    if sum(c.isdigit() for c in pw) < 2: e.append("2 digits")
    if sum(c.isupper() and c.isascii() for c in pw) < 2: e.append("2 uppercase")
    if sum(c.islower() and c.isascii() for c in pw) < 2: e.append("2 lowercase")
    if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/~`" for c in pw): e.append("1 special character")
    if username and username.lower() in pw.lower(): e.append("must not contain the username")
    if '"' in pw: e.append("no double quote")
    return e


def strong_password(n=18):
    rnd = secrets.SystemRandom()
    while True:
        chars = ([rnd.choice(string.ascii_uppercase) for _ in range(4)] +
                 [rnd.choice(string.ascii_lowercase) for _ in range(n - 10)] +
                 [rnd.choice(string.digits) for _ in range(4)] + [rnd.choice(SPECIAL) for _ in range(2)])
        rnd.shuffle(chars)
        pw = "".join(chars)
        if not password_problems(pw):
            return pw


TEMP_KEY_PY = """
import asyncio
from app.db.base import GetDB
from app.db.crud.temp_key import create_temp_key
async def main():
    async with GetDB() as db:
        k = await create_temp_key(db)
        print("KEY=" + str(getattr(k, "key", None) or k))
asyncio.run(main())
"""


def temp_key():
    out = subprocess.run([sys.executable, "-c", TEMP_KEY_PY], cwd=CODE, capture_output=True, text=True, timeout=120)
    for line in out.stdout.splitlines():
        if line.startswith("KEY="):
            return line[4:].strip()
    raise RuntimeError(f"temp key failed: {out.stderr[-600:]}")


def read_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def write_private(path, text):
    old = os.umask(0o077)
    try:
        open(path, "w").write(text)
    finally:
        os.umask(old)
    os.chmod(path, 0o600)


def login(username, password):
    global TOKEN
    code, res = req("POST", "/api/admin/token", {"username": username, "password": password}, form=True, auth=False)
    if code == 200 and isinstance(res, dict) and res.get("access_token"):
        TOKEN = res["access_token"]; return True
    return False


def relogin():
    st = read_state()
    return bool(st) and login(st["username"], st["password"])


def ensure_owner():
    st = read_state()
    username = st.get("username") or (os.getenv("ADMIN_USERNAME") or "sabigozar").strip()
    env_pw = (os.getenv("ADMIN_PASSWORD") or "").strip()
    if env_pw:
        bad = password_problems(env_pw, username)
        if bad:
            log("ADMIN_PASSWORD ignored, it needs:", ", ".join(bad)); env_pw = ""
    pw = env_pw or st.get("password") or strong_password()
    changed = pw != st.get("password")
    if not login(username, pw):
        code, res = req("POST", "/api/setup/owner", {"key": temp_key(), "username": username, "password": pw}, auth=False)
        if code in (200, 201):
            log("owner account created:", username)
        elif code != 409:
            log(f"owner create -> {code}: {str(res)[:200]}")
        if not login(username, pw):
            code, res = req("PATCH", "/api/setup/owner", {"key": temp_key(), "password": pw}, auth=False)
            if code == 200 and isinstance(res, dict):
                username = res.get("username") or username
                log("owner password reset (ADMIN_PASSWORD / recovery)")
            if not login(username, pw):
                raise RuntimeError(f"owner login failed ({code}: {str(res)[:200]})")
    write_private(STATE, json.dumps({"username": username, "password": pw,
                                     "source": "ADMIN_PASSWORD" if env_pw else "generated"}))
    CTX.update(username=username, password=pw, changed=changed, source="ADMIN_PASSWORD" if env_pw else "generated")


def ensure_core(seed):
    body = {"name": CORE_NAME, "config": protocols.core_config(seed, protocols.reality_settings(load_secrets())),
            "exclude_inbound_tags": [], "fallbacks_inbound_tags": []}
    for c in as_list(must("GET", "/api/cores"), "cores"):
        if c.get("name") == CORE_NAME:
            code, res = req("PUT", f"/api/core/{c['id']}?restart_nodes=true", body)
            if code not in (200, 201):
                code, res = req("PUT", f"/api/core/{c['id']}?restart_nodes=false", body)
            log("core updated" if code in (200, 201) else f"core update failed {code}: {str(res)[:200]}")
            return c["id"]
    c = must("POST", "/api/core", body); log("core created"); return c["id"]


def ensure_node(core_id, sec):
    cert = open(os.path.join(DATA, "certs", "node.pem")).read().strip()
    body = {"name": NODE_NAME, "address": "127.0.0.1", "port": 62050, "usage_coefficient": 1,
            "connection_type": "grpc", "server_ca": cert, "keep_alive": 60,
            "core_config_id": core_id, "api_key": sec["NODE_API_KEY"]}
    for n in as_list(must("GET", "/api/nodes"), "nodes"):
        if n.get("name") == NODE_NAME:
            must("PUT", f"/api/node/{n['id']}", body); log("node updated"); return n["id"]
    n = must("POST", "/api/node", body); log("node created"); return n["id"]


def wait_node(node_id, seconds=90):
    st, n = None, None
    for _ in range(seconds // 3):
        code, n = req("GET", f"/api/node/{node_id}")
        st = n.get("status") if code == 200 and isinstance(n, dict) else None
        if st == "connected":
            log("Xray node connected ✓", n.get("xray_version") or ""); return True
        time.sleep(3)
    log("WARNING: node status =", st, n.get("message") if isinstance(n, dict) else "")
    return False


def ensure_group():
    last = None
    for _ in range(15):
        try:
            for g in as_list(must("GET", "/api/groups"), "groups"):
                if g.get("name") == GROUP_NAME:
                    must("PUT", f"/api/group/{g['id']}", {"name": GROUP_NAME, "inbound_tags": protocols.TAGS})
                    return g["id"]
            g = must("POST", "/api/group", {"name": GROUP_NAME, "inbound_tags": protocols.TAGS})
            log("group created"); return g["id"]
        except Exception as e:
            last = e; time.sleep(3)
    raise RuntimeError(f"group: {last}")


def tcp_proxy():
    d = (os.getenv("RAILWAY_TCP_PROXY_DOMAIN") or os.getenv("TCP_PROXY_DOMAIN") or "").strip()
    p = (os.getenv("RAILWAY_TCP_PROXY_PORT") or os.getenv("TCP_PROXY_PORT") or "").strip()
    app = (os.getenv("RAILWAY_TCP_APPLICATION_PORT") or "").strip()
    if app and app != str(protocols.REALITY_PORT):
        log(f"WARNING: TCP Proxy targets port {app}; set it to {protocols.REALITY_PORT} for Reality")
    return (d, int(p)) if d and p.isdigit() else None


def ensure_hosts(seed):
    reality, tcp = protocols.reality_settings(load_secrets()), tcp_proxy()
    clean = [x.strip() for x in os.getenv("CLEAN_IPS", "").split(",") if x.strip()]
    wanted = protocols.host_bodies(seed, DOMAIN, TITLE, reality=reality, tcp=tcp, clean_ips=clean,
                                   fragment=env_bool("FRAGMENT_HOST", True), mux=env_bool("MUX", False))
    if not DOMAIN:
        log("WARNING: no public domain yet -> Settings > Networking > Generate Domain, then redeploy")
    if reality and not tcp:
        log(f"Reality ready on :{protocols.REALITY_PORT} -> add a TCP Proxy (port {protocols.REALITY_PORT}) to publish it")
    try:
        managed = set(json.load(open(HOSTS_STATE)))
    except Exception:
        managed = set()
    by_remark = {}
    for h in as_list(must("GET", "/api/hosts"), "hosts"):
        ours = h.get("id") in managed or (str(h.get("inbound_tag") or "").startswith("SG-")
                                          and str(h.get("remark") or "").endswith(f"| {TITLE}"))
        if ours:
            by_remark.setdefault(h.get("remark"), []).append(h)
    keep = set()
    for body in wanted:
        mine = by_remark.pop(body["remark"], [])
        if mine:
            must("PUT", f"/api/host/{mine[0]['id']}", {**body, "id": mine[0]["id"]}); keep.add(mine[0]["id"])
            for extra in mine[1:]:
                req("DELETE", f"/api/host/{extra['id']}")
        else:
            res = must("POST", "/api/host/", body)
            if isinstance(res, dict) and res.get("id") is not None:
                keep.add(res["id"])
    for stale in by_remark.values():
        for h in stale:
            req("DELETE", f"/api/host/{h['id']}")
    write_private(HOSTS_STATE, json.dumps(sorted(keep)))
    log(f"{len(wanted)} configs ready" + (f" on {DOMAIN}" if DOMAIN else "") +
        (f" + Reality on {tcp[0]}:{tcp[1]}" if reality and tcp else ""))


def ensure_settings():
    code, s = req("GET", "/api/settings")
    if code != 200 or not isinstance(s, dict) or "subscription" not in s:
        log("settings endpoint not as expected, skipped"); return
    sub = s["subscription"]
    if DOMAIN:
        sub["url_prefix"] = f"https://{DOMAIN}"
    sub["profile_title"] = TITLE
    sub["support_url"] = SUPPORT
    sub["update_interval"] = int(os.getenv("SUB_UPDATE_HOURS", "6"))
    code, res = req("PUT", "/api/settings", {"subscription": sub})
    log("subscription settings ok" if code in (200, 201) else f"subscription settings skipped ({code}: {str(res)[:200]})")


def attach_orphans(group_id):
    offset = 0
    while True:
        code, res = req("GET", f"/api/users?offset={offset}&limit=200")
        if code == 401 and relogin():
            continue
        if code != 200:
            return
        users = as_list(res, "users")
        for u in users:
            if not u.get("group_ids"):
                c, r = req("PUT", f"/api/user/{urllib.parse.quote(u['username'])}", {"group_ids": [group_id]})
                log(f"all configs attached to {u['username']}" if c == 200 else f"attach {u['username']} -> {c}")
        if len(users) < 200:
            return
        offset += 200


def run_features():
    try:
        import features  # noqa
    except ImportError:
        return
    try:
        features.run(req=req, must=must, as_list=as_list, log=log, ctx=CTX, relogin=relogin)
    except Exception as e:
        log("features error:", e)


def banner():
    url = f"https://{DOMAIN}/dashboard/" if DOMAIN else "(generate a Railway domain first)"
    lines = ["", "╔══════════════════════ SABIGOZAR ══════════════════════╗",
             f"  Panel     : {url}", f"  Username  : {CTX['username']}"]
    if env_bool("HIDE_PASSWORD_IN_LOGS") and not CTX.get("changed"):
        lines.append("  Password  : (hidden, HIDE_PASSWORD_IN_LOGS=1)")
    else:
        lines.append(f"  Password  : {CTX['password']}")
    lines += [f"  Source    : {CTX['source']}", "  Support   : Telegram @SAHEBKARAMI",
              "╚═══════════════════════════════════════════════════════╝", ""]
    for l in lines:
        print(l, flush=True)
    write_private(os.path.join(DATA, "CREDENTIALS.txt"), "\n".join(lines[2:6]) + "\n")


def step(name, fn, *a):
    try:
        return fn(*a)
    except Exception as e:
        log(f"{name} failed: {e}")


def main():
    sec = load_secrets()
    seed = sec.get("PATH_SEED") or "sabigozar"
    wait_panel()
    ensure_owner()
    core_id = ensure_core(seed)
    node_id = step("node", ensure_node, core_id, sec)
    gid = ensure_group()
    CTX.update(group_id=gid, core_id=core_id, seed=seed, domain=DOMAIN, node_id=node_id)
    step("hosts", ensure_hosts, seed)
    step("settings", ensure_settings)
    run_features()
    if node_id:
        step("node check", wait_node, node_id)
    banner()
    if env_bool("BOOTSTRAP_ONESHOT"):
        attach_orphans(gid); return
    log("watcher on: new users get every config automatically")
    while True:
        step("watcher", attach_orphans, gid)
        time.sleep(max(2, int(os.getenv("WATCH_SECONDS", "20"))))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("FATAL", e); sys.exit(1)
