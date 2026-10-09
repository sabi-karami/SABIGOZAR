"""SABIGOZAR protocol catalogue  ·  @SAHEBKARAMI

HTTPS inbounds listen on 127.0.0.1; nginx routes /<seed>/<route> to them and Railway's edge adds
TLS on 443. <seed> is random per install, so no two SABIGOZAR servers share paths.
VLESS-Reality-Vision listens on 0.0.0.0:8443 and is published through Railway's TCP Proxy."""
import copy
import os

# tag               proto     port   network        route fp         label
INBOUNDS = [
    ("SG-VLESS-WS",    "vless",  10001, "ws",          "vw", "chrome",  "⚡ VLESS-WS"),
    ("SG-VLESS-HU",    "vless",  10002, "httpupgrade", "vh", "firefox", "🚀 VLESS-HTTPUpgrade"),
    ("SG-VLESS-XHTTP", "vless",  10003, "xhttp",       "vx", "chrome",  "🌀 VLESS-XHTTP"),
    ("SG-TROJAN-WS",   "trojan", 10004, "ws",          "tw", "safari",  "🛡 Trojan-WS"),
    ("SG-VMESS-WS",    "vmess",  10005, "ws",          "mw", "edge",    "💎 VMess-WS"),
    ("SG-TROJAN-HU",   "trojan", 10006, "httpupgrade", "th", "ios",     "🔥 Trojan-HTTPUpgrade"),
]
REALITY_TAG = "SG-VLESS-REALITY"
REALITY_PORT = int(os.getenv("REALITY_PORT", "8443"))
REALITY_LABEL = "🟢 VLESS-Reality LowPing"
DEFAULT_REALITY_SNI = "www.cloudflare.com"
TAGS = [i[0] for i in INBOUNDS] + [REALITY_TAG]
EARLY_DATA = "?ed=2560"
FRAGMENT = {"xray": {"packets": "tlshello", "length": "100-200", "interval": "10-20"}}
MUX = {"xray": {"enabled": True, "concurrency": 8, "xudp_concurrency": 16, "xudp_proxy_udp_443": "reject"}}


def path(seed, route):
    return f"/{seed}/{route}"


def reality_settings(secrets_map):
    pk = (os.getenv("REALITY_PRIVATE_KEY") or secrets_map.get("REALITY_PRIVATE_KEY") or "").strip()
    if not pk:
        return None
    sni = [s.strip() for s in (os.getenv("REALITY_SNI") or DEFAULT_REALITY_SNI).split(",") if s.strip()]
    sid = (os.getenv("REALITY_SHORT_ID") or secrets_map.get("REALITY_SHORT_ID") or "").strip()
    return {"private_key": pk, "short_ids": [sid] if sid else ["a1b2c3d4"], "server_names": sni,
            "dest": (os.getenv("REALITY_DEST") or f"{sni[0]}:443").strip()}


def inbound(tag, proto, port, net, p):
    stream = {"network": net, "security": "none"}
    if net == "ws":
        stream["wsSettings"] = {"path": p}
    elif net == "httpupgrade":
        stream["httpupgradeSettings"] = {"path": p}
    elif net == "xhttp":
        stream["xhttpSettings"] = {"path": p, "mode": "auto"}
    settings = {"clients": []}
    if proto == "vless":
        settings["decryption"] = "none"
    return {"tag": tag, "listen": "127.0.0.1", "port": port, "protocol": proto,
            "settings": settings, "streamSettings": stream,
            "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": True}}


def reality_inbound(r):
    return {"tag": REALITY_TAG, "listen": "0.0.0.0", "port": REALITY_PORT, "protocol": "vless",
            "settings": {"clients": [], "decryption": "none", "flow": "xtls-rprx-vision"},
            "streamSettings": {"network": "tcp", "security": "reality",
                               "realitySettings": {"show": False, "dest": r["dest"], "xver": 0,
                                                   "serverNames": r["server_names"],
                                                   "privateKey": r["private_key"], "shortIds": r["short_ids"]}},
            "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": True}}


def core_config(seed, reality=None):
    inbounds = [inbound(t, pr, po, n, path(seed, r)) for t, pr, po, n, r, _, _ in INBOUNDS]
    if reality:
        inbounds.append(reality_inbound(reality))
    return {
        "log": {"loglevel": "warning"},
        "dns": {"servers": ["https+local://1.1.1.1/dns-query", "https+local://8.8.8.8/dns-query", "localhost"],
                "queryStrategy": "UseIPv4"},
        "inbounds": inbounds,
        "outbounds": [
            {"protocol": "freedom", "tag": "DIRECT", "settings": {"domainStrategy": "UseIPv4"}},
            {"protocol": "blackhole", "tag": "BLOCK"},
        ],
        "routing": {"domainStrategy": "IPIfNonMatch", "rules": [
            {"type": "field", "ip": ["geoip:private"], "outboundTag": "BLOCK"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "BLOCK"},
        ]},
        "policy": {"levels": {"0": {"handshake": 4, "connIdle": 300, "uplinkOnly": 1, "downlinkOnly": 1, "bufferSize": 512}}},
    }


def host_bodies(seed, domain, title="SABIGOZAR", reality=None, tcp=None, clean_ips=(), fragment=True, mux=False):
    """Every host SABIGOZAR manages. Remarks are the identity key (must stay unique)."""
    out = []
    if reality and tcp:
        out.append({"remark": f"{REALITY_LABEL} | {title}", "address": [tcp[0]], "inbound_tag": REALITY_TAG,
                    "port": tcp[1], "sni": [reality["server_names"][0]], "host": [], "path": None,
                    "security": "inbound_default", "alpn": [], "fingerprint": "chrome",
                    "priority": 0, "is_disabled": False})
    if not domain:
        return out
    base = []
    for idx, (tag, proto, port, net, route, fp, label) in enumerate(INBOUNDS):
        p = path(seed, route)
        b = {"remark": f"{label} | {title}", "address": [domain], "inbound_tag": tag, "port": 443,
             "sni": [domain], "host": [domain], "path": p + (EARLY_DATA if net == "ws" else ""),
             "security": "tls", "alpn": ["http/1.1"], "fingerprint": fp, "allowinsecure": False,
             "priority": idx + 1, "is_disabled": False}
        if net == "xhttp":
            b["transport_settings"] = {"xhttp_settings": {"mode": "packet-up"}}
        if mux and net in ("ws", "httpupgrade"):
            b["mux_settings"] = copy.deepcopy(MUX)
        base.append(b)
    out += base
    ws = base[0]
    if fragment:
        f = copy.deepcopy(ws)
        f.update(remark=f"🧩 VLESS-WS Fragment | {title}", priority=20, fragment_settings=copy.deepcopy(FRAGMENT))
        f.pop("mux_settings", None)
        out.append(f)
    for i, ip in enumerate(clean_ips):
        c = copy.deepcopy(ws)
        c.update(remark=f"☁️ CDN {ip} | {title}", address=[ip], priority=30 + i)
        out.append(c)
    return out
