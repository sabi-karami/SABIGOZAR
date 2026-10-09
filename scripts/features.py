"""SABIGOZAR extras  ·  @SAHEBKARAMI
reseller role · sale templates · Telegram bot & notifications · DB backups (local + Telegram)
· watchdog (auto-reconnect the Xray node). Every feature is optional and never blocks setup."""
import gzip, os, shutil, sqlite3, threading, time, urllib.parse, urllib.request, uuid

GB, DAY = 1024 ** 3, 86400
RESELLER_ROLE = "نماینده SABIGOZAR"
TEMPLATES = [
    ("SABIGOZAR 10GB · 30 روز", 10, 30), ("SABIGOZAR 20GB · 30 روز", 20, 30),
    ("SABIGOZAR 30GB · 30 روز", 30, 30), ("SABIGOZAR 50GB · 30 روز", 50, 30),
    ("SABIGOZAR 100GB · 30 روز", 100, 30), ("SABIGOZAR 200GB · 60 روز", 200, 60),
    ("SABIGOZAR نامحدود · 30 روز", 0, 30), ("SABIGOZAR تست · 1GB · 1 روز", 1, 1),
]
API = {}


def env(k, d=""):
    return (os.getenv(k) or d).strip()


def on(k, d=True):
    v = os.getenv(k)
    return d if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def ensure_templates(gid):
    req, must, as_list, log = API["req"], API["must"], API["as_list"], API["log"]
    have = {t.get("name"): t for t in as_list(must("GET", "/api/user_templates"), "templates")}
    ids = []
    for name, gb, days in TEMPLATES:
        body = {"name": name, "data_limit": gb * GB, "expire_duration": days * DAY, "group_ids": [gid],
                "status": "active", "data_limit_reset_strategy": "no_reset"}
        if name in have:
            ids.append(have[name]["id"]); continue
        code, res = req("POST", "/api/user_template", body)
        if code in (200, 201) and isinstance(res, dict):
            ids.append(res.get("id"))
        else:
            log(f"template '{name}' -> {code}: {str(res)[:160]}")
    log(f"{len(ids)} sale templates ready")


def ensure_reseller_role(gid):
    req, as_list, log = API["req"], API["as_list"], API["log"]
    own = {"scope": 1}
    role = {"name": RESELLER_ROLE,
            "permissions": {"users": {"create": own, "read": own, "read_simple": own, "update": own, "delete": own,
                                      "reset_usage": own, "revoke_sub": own, "activate_next_plan": own},
                            "templates": {"read": True, "read_simple": True},
                            "groups": {"read_simple": True}, "system": {"read": True},
                            "settings": {"read_general": True}},
            "access": {"require_template": on("RESELLER_REQUIRE_TEMPLATE", True), "allowed_group_ids": [gid]},
            "disabled_when_limited": True}
    code, res = req("GET", "/api/admin-roles")
    if code != 200:
        log("reseller role: endpoint not available"); return None
    for r in as_list(res, "roles"):
        if r.get("name") == RESELLER_ROLE:
            req("PUT", f"/api/admin-role/{r['id']}", role); return r["id"]
    code, res = req("POST", "/api/admin-role", role)
    if code in (200, 201) and isinstance(res, dict):
        log("reseller role created:", RESELLER_ROLE); return res.get("id")
    log(f"reseller role -> {code}: {str(res)[:200]}")


def ensure_telegram(ctx):
    req, log = API["req"], API["log"]
    token, admin_id = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_ADMIN_ID")
    if not token:
        return
    if admin_id.lstrip("-").isdigit():
        c, r = req("PUT", f"/api/admin/{urllib.parse.quote(ctx['username'])}", {"telegram_id": int(admin_id)})
        log("owner linked to Telegram id" if c == 200 else f"owner telegram link -> {c}: {str(r)[:160]}")
    code, s = req("GET", "/api/settings")
    if code != 200 or not isinstance(s, dict):
        return
    patch = {}
    if on("TELEGRAM_BOT", True) and isinstance(s.get("telegram"), dict):
        tg = dict(s["telegram"])
        tg.update(enable=True, token=token, method="long-polling", for_admins_only=True, mini_app_login=False)
        patch["telegram"] = tg
    ns = s.get("notification_settings")
    if admin_id.lstrip("-").isdigit() and isinstance(ns, dict) and on("TELEGRAM_NOTIFY", True):
        ns = dict(ns); ns.update(notify_telegram=True, telegram_api_token=token, telegram_chat_id=int(admin_id))
        ns["max_retries"] = max(int(ns.get("max_retries") or 3), 2)
        patch["notification_settings"] = ns
    if patch:
        c, r = req("PUT", "/api/settings", patch)
        log("Telegram bot & notifications on ✓" if c in (200, 201) else f"telegram settings -> {c}: {str(r)[:200]}")


def tg_send(text=None, file_path=None, caption=""):
    token, chat = env("TELEGRAM_BOT_TOKEN"), env("BACKUP_CHAT_ID") or env("TELEGRAM_ADMIN_ID")
    if not token or not chat:
        return False
    base = f"https://api.telegram.org/bot{token}/"
    try:
        if file_path is None:
            data = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
            urllib.request.urlopen(base + "sendMessage", data=data, timeout=30).read(); return True
        b = "----sabigozar" + uuid.uuid4().hex
        parts = []
        for k, v in (("chat_id", chat), ("caption", caption)):
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        name = os.path.basename(file_path)
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="document"; filename="{name}"\r\n'
                     f"Content-Type: application/gzip\r\n\r\n".encode() + open(file_path, "rb").read() + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        r = urllib.request.Request(base + "sendDocument", data=b"".join(parts),
                                   headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        urllib.request.urlopen(r, timeout=120).read(); return True
    except Exception as e:
        API["log"]("telegram send failed:", str(e)[:160]); return False


def db_path():
    url = env("SQLALCHEMY_DATABASE_URL")
    return url.split(":///", 1)[1] if url.startswith("sqlite") and ":///" in url else None


def backup_once(reason="scheduled"):
    src = db_path()
    if not src or not os.path.exists(src):
        return None
    d = os.path.join(env("SABI_DATA", "/var/lib/sabigozar"), "backups"); os.makedirs(d, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    raw, out = os.path.join(d, f".tmp-{stamp}.sqlite3"), os.path.join(d, f"sabigozar-{stamp}.sqlite3.gz")
    s, t = sqlite3.connect(src), sqlite3.connect(raw)
    try:
        s.backup(t)
    finally:
        t.close(); s.close()
    with open(raw, "rb") as fi, gzip.open(out, "wb", 6) as fo:
        shutil.copyfileobj(fi, fo)
    os.remove(raw)
    keep = int(env("BACKUP_KEEP", "7"))
    old = sorted(f for f in os.listdir(d) if f.startswith("sabigozar-") and f.endswith(".gz"))
    for f in old[:-keep] if keep > 0 else []:
        os.remove(os.path.join(d, f))
    size = os.path.getsize(out) // 1024
    sent = tg_send(file_path=out, caption=f"🗄 SABIGOZAR backup · {stamp} · {size} KB · {reason}\n@SAHEBKARAMI")
    API["log"](f"backup saved ({size} KB)" + (" + sent to Telegram" if sent else ""))
    return out


def backup_loop():
    time.sleep(int(env("BACKUP_FIRST_DELAY", "600")))
    while True:
        try:
            backup_once()
        except Exception as e:
            API["log"]("backup failed:", e)
        time.sleep(max(1, int(float(env("BACKUP_HOURS", "24")) * 3600)))


def watchdog_loop(node_id):
    req, log = API["req"], API["log"]
    bad = 0
    while True:
        time.sleep(int(env("WATCHDOG_SECONDS", "60")))
        try:
            code, n = req("GET", f"/api/node/{node_id}")
            if code == 401 and API["relogin"]():
                continue
            st = n.get("status") if code == 200 and isinstance(n, dict) else None
            if st == "connected":
                if bad >= 2:
                    tg_send("✅ SABIGOZAR: Xray core is back online.")
                bad = 0; continue
            bad += 1
            log(f"watchdog: node status={st}, reconnecting (#{bad})")
            req("POST", f"/api/node/{node_id}/reconnect")
            if bad == 2:
                tg_send(f"⚠️ SABIGOZAR: Xray core is {st}. Auto-reconnect in progress.")
        except Exception as e:
            log("watchdog error:", e)


def start(name, fn, *a):
    threading.Thread(target=fn, args=a, name=name, daemon=True).start()


def run(req, must, as_list, log, ctx, relogin=None):
    API.update(req=req, must=must, as_list=as_list, log=log, relogin=relogin or (lambda: False))
    gid = ctx.get("group_id")
    for name, fn in (("templates", lambda: ensure_templates(gid)), ("reseller", lambda: ensure_reseller_role(gid)),
                     ("telegram", lambda: ensure_telegram(ctx))):
        try:
            if name == "reseller" and not on("RESELLER_ROLE", True):
                continue
            fn()
        except Exception as e:
            log(f"{name} failed:", e)
    if on("BACKUP", True) and db_path():
        start("backup", backup_loop)
    if ctx.get("node_id") and on("WATCHDOG", True):
        start("watchdog", watchdog_loop, ctx["node_id"])
    if ctx.get("changed") and env("TELEGRAM_BOT_TOKEN"):
        tg_send(f"🛡 SABIGOZAR panel is ready\nPanel: https://{ctx.get('domain') or '-'}/dashboard/\n"
                f"Username: {ctx['username']}\nPassword: {ctx['password']}\n\nSupport: @SAHEBKARAMI")
