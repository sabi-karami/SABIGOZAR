"""SABIGOZAR rebrand: runs once at docker build time on the official PasarGuard image.
- Every visible "PasarGuard" -> "SABIGOZAR" (titles, logos, locales, API title, Telegram texts)
- Support / donate / community links -> Telegram @SAHEBKARAMI
- Remote ad feed and GitHub update checks disabled (point to a local 404)
Never fails the build: unknown patterns are only reported."""
import json, os, re, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/code"
BRANDING = sys.argv[2] if len(sys.argv) > 2 else "/opt/sabigozar/branding"
BRAND, TG = "SABIGOZAR", "https://t.me/SAHEBKARAMI"
OFF = "/__sabigozar/off"
BUILD = os.path.join(ROOT, "dashboard", "build")
stats = {"files": 0, "hits": 0}

JS_LITERAL = [
    ("https://api.github.com/repos/pasarguard/ads/contents/config.json", OFF),
    ("https://api.github.com/repos/pasarguard/ads/contents/goal.json", OFF),
    ("https://api.github.com/repos/PasarGuard/panel/releases/latest", OFF),
    ("https://api.github.com/repos/PasarGuard/node/releases/latest", OFF),
    ("https://github.com/PasarGuard/panel/releases/latest", TG),
    ("https://github.com/PasarGuard/panel", TG),
    ("https://donate.pasarguard.org/", TG),
    ("https://donate.pasarguard.org", TG),
    ("https://t.me/Pasar_Guard", TG),
    ("`PasarGuard Logo`", "`SABIGOZAR Logo`"),
    ("`Star PasarGuard on GitHub`", "`SABIGOZAR`"),
    ("`Support PasarGuard`", "`SABIGOZAR`"),
    ("improve PasarGuard and build", "improve SABIGOZAR and build"),
    ("`Remark (e.g. PasarGuard-Host)`", "`Remark (e.g. SABIGOZAR-Host)`"),
    ("children:`PasarGuard`", "children:`SABIGOZAR`"),
]
JS_REGEX = [(re.compile(r"https://github\.com/PasarGuard(?=`)"), TG)]
VISIBLE = re.compile(r"(?i)pasar\s?guard|پاسارگارد|پاسارگاد")
DONATION = {
    "fa": {"title": "پشتیبانی SABIGOZAR", "message": "برای پشتیبانی، تمدید و خرید با آیدی تلگرام @SAHEBKARAMI در ارتباط باشید.", "donate": "تلگرام @SAHEBKARAMI"},
    "en": {"title": "SABIGOZAR Support", "message": "For support and renewals contact @SAHEBKARAMI on Telegram.", "donate": "Telegram @SAHEBKARAMI"},
}

def rw(path, fn):
    try:
        s = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, FileNotFoundError):
        return
    n = fn(s)
    if n != s:
        open(path, "w", encoding="utf-8").write(n); stats["files"] += 1

def js_fix(s):
    for a, b in JS_LITERAL:
        if a in s:
            stats["hits"] += s.count(a); s = s.replace(a, b)
    for rx, b in JS_REGEX:
        s, k = rx.subn(b, s); stats["hits"] += k
    return s

def html_fix(s):
    s = re.sub(r"<title>[^<]*</title>", f"<title>{BRAND}</title>", s, count=1)
    return VISIBLE.sub(BRAND, s)

def locale_fix(lang):
    def walk(o):
        if isinstance(o, dict): return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list): return [walk(v) for v in o]
        if isinstance(o, str): return VISIBLE.sub(BRAND, o)
        return o
    def fn(s):
        d = walk(json.loads(s))
        don = d.get("donation")
        if isinstance(don, dict):
            for k, v in DONATION.get(lang, DONATION["en"]).items():
                if k in don: don[k] = v
        d["pasarguard"] = BRAND
        return json.dumps(d, ensure_ascii=False, indent=2)
    return fn

def main():
    if not os.path.isdir(BUILD):
        print("[rebrand] dashboard build not found, skipped"); return
    for dp, _, fs in os.walk(BUILD):
        for f in fs:
            p = os.path.join(dp, f)
            if f.endswith(".js"): rw(p, js_fix)
            elif f.endswith(".html"): rw(p, html_fix)
            elif f.endswith(".webmanifest"):
                rw(p, lambda s: re.sub(r'"(name|short_name)"\s*:\s*"[^"]*"', lambda m: f'"{m.group(1)}":"{BRAND}"', s))
    loc = os.path.join(BUILD, "statics", "locales")
    for f in os.listdir(loc) if os.path.isdir(loc) else []:
        if f.endswith(".json"): rw(os.path.join(loc, f), locale_fix(f[:-5]))
    fav_src, fav_dst = os.path.join(BRANDING, "favicon"), os.path.join(BUILD, "statics", "favicon")
    if os.path.isdir(fav_src) and os.path.isdir(fav_dst):
        for f in os.listdir(fav_src):
            shutil.copyfile(os.path.join(fav_src, f), os.path.join(fav_dst, f))
    rw(os.path.join(ROOT, "app", "app_factory.py"), lambda s: s.replace('title="PasarGuardAPI"', 'title="SABIGOZAR API"')
       .replace('f"PasarGuard v{__version__}', 'f"SABIGOZAR · core v{__version__}').replace("removed in PasarGuard 7", "removed in SABIGOZAR core 7"))
    tg = os.path.join(ROOT, "app", "telegram")
    for dp, _, fs in os.walk(tg):
        for f in fs:
            if f.endswith(".py"):
                rw(os.path.join(dp, f), lambda s: s.replace('"PasarGuard Version"', '"SABIGOZAR Version"').replace("PasarGuard Bot", "SABIGOZAR Bot"))
    for t in ("home/index.html", "subscription/index.html"):
        rw(os.path.join(ROOT, "app", "templates", t), html_fix)
    print(f"[rebrand] SABIGOZAR applied: {stats['files']} files changed, {stats['hits']} link/text patches")

if __name__ == "__main__":
    try: main()
    except Exception as e: print("[rebrand] WARNING:", e)
