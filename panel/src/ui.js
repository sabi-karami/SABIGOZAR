// SABIGOZAR Deploy Panel page (generated from ui.html)
export default `<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#121315">
<title>SABIGOZAR · پنل نصب خودکار</title>
<style>
@font-face{font-family:Vazirmatn;src:url(https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/webfonts/Vazirmatn[wght].woff2) format("woff2-variations");font-weight:100 900;font-display:swap}
:root{--bg:#121315;--card:#1a1b1e;--card2:#222327;--bd:rgba(255,255,255,.08);--fg:#fafafa;--mut:#8d919c;--pri:#3b82f6;--pri2:#6366f1;--ok:#22c55e;--warn:#f59e0b;--bad:#ef4444;--grid:rgba(255,255,255,.035);--glow:rgba(37,99,235,.17);color-scheme:dark}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--fg);font-family:Vazirmatn,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
body{min-height:100dvh;background:radial-gradient(55% 45% at 12% 25%,var(--glow),transparent 72%),radial-gradient(50% 40% at 88% 85%,var(--glow),transparent 72%),linear-gradient(var(--grid) 1px,transparent 1px) 0 0/40px 40px,linear-gradient(90deg,var(--grid) 1px,transparent 1px) 0 0/40px 40px,var(--bg);background-attachment:fixed}
.wrap{max-width:860px;margin:0 auto;padding:26px 16px 50px;display:flex;flex-direction:column;gap:14px}
.hd{display:flex;gap:12px;align-items:center}.logo{width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,var(--pri),var(--pri2));display:grid;place-items:center;font-size:24px;box-shadow:0 8px 24px -8px var(--pri)}
h1{margin:0;font-size:22px;font-weight:800}.sub{color:var(--mut);font-size:12.5px;margin-top:3px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:18px}
h2{margin:0 0 12px;font-size:15px;display:flex;gap:8px;align-items:center}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:640px){.grid{grid-template-columns:1fr}}
label{display:flex;flex-direction:column;gap:6px;font-size:12.5px;color:var(--mut);font-weight:600}
label small{font-weight:400;font-size:11px;line-height:1.7}label small a{color:var(--pri)}
input,select,textarea{width:100%;background:var(--card2);border:1px solid var(--bd);border-radius:11px;color:var(--fg);padding:11px 12px;font:inherit;font-size:13.5px;outline:none;direction:ltr;text-align:left}
input:focus,select:focus,textarea:focus{border-color:var(--pri)}textarea{min-height:64px;resize:vertical}
.req::after{content:" *";color:var(--bad)}
.chk{flex-direction:row;align-items:center;gap:8px;color:var(--fg)}.chk input{width:auto}
details summary{cursor:pointer;font-weight:700;font-size:13.5px;color:var(--mut);padding:4px 0}details[open] summary{margin-bottom:12px}
.btn{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;height:52px;border:0;border-radius:13px;background:linear-gradient(135deg,var(--pri),var(--pri2));color:#fff;font:inherit;font-weight:800;font-size:16px;cursor:pointer;box-shadow:0 12px 30px -12px var(--pri);transition:filter .2s,transform .15s}
.btn:hover{filter:brightness(1.1)}.btn:active{transform:scale(.98)}.btn:disabled{opacity:.55;cursor:wait}
.btn.gh{background:var(--card2);border:1px solid var(--bd);box-shadow:none;height:42px;font-size:13.5px}
.row{display:flex;gap:8px;flex-wrap:wrap}.row .btn{flex:1;min-width:150px}
.steps{display:flex;flex-direction:column;gap:6px}
.st{display:flex;gap:10px;align-items:center;padding:9px 12px;border-radius:11px;background:var(--card2);font-size:13.5px}
.st i{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-style:normal;font-size:12px;background:var(--card);color:var(--mut);flex:none}
.st.run i{background:var(--pri);color:#fff;animation:pl 1.2s infinite}.st.ok i{background:var(--ok);color:#fff}.st.err i{background:var(--bad);color:#fff}.st.warn i{background:var(--warn);color:#fff}
.st span{flex:1}.st small{color:var(--mut);font-size:11.5px}
@keyframes pl{50%{box-shadow:0 0 0 6px rgba(59,130,246,.2)}}
.log{background:#0c0d0f;border:1px solid var(--bd);border-radius:12px;padding:12px;height:260px;overflow:auto;font:12px/1.75 ui-monospace,Menlo,Consolas,monospace;direction:ltr;text-align:left;white-space:pre-wrap;word-break:break-all}
.log .ok{color:#4ade80}.log .warn{color:#fbbf24}.log .err{color:#f87171}.log .info{color:#cbd5e1}.log .h{color:#93c5fd;font-weight:700}
.bar{height:8px;border-radius:8px;background:var(--card2);overflow:hidden;margin-bottom:12px}.bar b{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--pri),var(--ok));transition:width .5s}
.rep{display:flex;flex-direction:column;gap:10px}
.kv{display:grid;grid-template-columns:170px 1fr auto;gap:8px;align-items:center;padding:9px 12px;background:var(--card2);border-radius:11px;font-size:13px}
.kv b{color:var(--mut);font-weight:600}.kv code{direction:ltr;text-align:left;word-break:break-all;font-size:12.5px}.kv button{background:var(--card);border:1px solid var(--bd);color:var(--fg);border-radius:8px;padding:4px 10px;font:inherit;font-size:12px;cursor:pointer}
@media(max-width:640px){.kv{grid-template-columns:1fr auto}.kv b{grid-column:1/-1}}
.note{padding:11px 13px;border-radius:12px;font-size:12.5px;line-height:1.9;background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3)}
.note.ok{background:rgba(34,197,94,.1);border-color:rgba(34,197,94,.3)}.note.bad{background:rgba(239,68,68,.1);border-color:rgba(239,68,68,.35)}
.hide{display:none!important}.mut{color:var(--mut);font-size:12px;line-height:1.9}
.lock{max-width:380px;margin:12vh auto 0}
.toast{position:fixed;left:50%;bottom:22px;transform:translate(-50%,40px);opacity:0;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 16px;font-size:13px;font-weight:700;transition:all .3s}.toast.on{opacity:1;transform:translate(-50%,0)}
</style>
</head>
<body>
<div class="wrap lock" id="lockV">
  <div class="hd"><div class="logo">🛡</div><div><h1>SABIGOZAR</h1><div class="sub">پنل نصب خودکار · Railway + Cloudflare</div></div></div>
  <div class="card"><label>رمز پنل<input type="password" id="pk" autocomplete="current-password"></label><div style="height:12px"></div><button class="btn" id="loginB">ورود</button><div class="mut" id="loginE" style="margin-top:8px"></div></div>
</div>

<div class="wrap hide" id="appV">
  <div class="hd"><div class="logo">🛡</div><div><h1>پنل نصب خودکار SABIGOZAR</h1><div class="sub">کلیدها را وارد کن، یک دکمه بزن؛ همه‌چیز ساخته، تنظیم و تست می‌شود.</div></div></div>

  <div class="note">🔒 کلیدها فقط برای همین نصب به Railway، Cloudflare و GitHub فرستاده می‌شوند و هیچ‌جا ذخیره نمی‌شوند (نه روی سرور، نه در مرورگر). بعد از نصب اگر لازمشان نداری، باطلشان کن.</div>

  <div class="card" id="formC">
    <h2>🔑 کلیدها</h2>
    <div class="grid">
      <label class="req">Railway Token<input type="password" id="railwayToken" autocomplete="off" placeholder="xxxxxxxx-xxxx-…"><small>railway.com ← Account Settings ← Tokens ← Create (نوع Account/Workspace). <a href="https://railway.com/account/tokens" target="_blank" rel="noopener">باز کردن</a></small></label>
      <label class="req">Cloudflare API Token<input type="password" id="cfToken" autocomplete="off"><small>دسترسی: Zone:Read، DNS:Edit، Zone Settings:Edit. <a href="https://dash.cloudflare.com/profile/api-tokens" target="_blank" rel="noopener">باز کردن</a></small></label>
      <label>GitHub Token (اختیاری)<input type="password" id="ghToken" autocomplete="off"><small>برای Fork یا Sync خودکار ریپو. دسترسی Contents: Read and write. <a href="https://github.com/settings/personal-access-tokens" target="_blank" rel="noopener">باز کردن</a></small></label>
      <label class="req">دامنه‌ی پنل VPN<input id="domain" placeholder="sabigozar.example.com"><small>ساب‌دامینی که پنل و لینک‌های ساب روی آن می‌نشینند. نباید همان آدرس این پنل باشد.</small></label>
    </div>
    <div style="height:14px"></div>
    <h2>👤 ورود به پنل VPN</h2>
    <div class="grid">
      <label>ADMIN_USERNAME<input id="adminUser" value="sabigozar"></label>
      <label>ADMIN_PASSWORD (خالی = خودکار)<input type="password" id="adminPass" autocomplete="new-password"><small>خالی بگذار: اگر از قبل هست همان می‌ماند، وگرنه یک رمز قوی ۱۸ کاراکتری ساخته می‌شود.</small></label>
    </div>
    <div style="height:14px"></div>
    <details>
      <summary>⚙️ تنظیمات بیشتر (اختیاری)</summary>
      <div class="grid">
        <label>ریپوی GitHub برای Railway<input id="repo" placeholder="sabi-0001/SABIGOZAR"><small>خالی: با GitHub Token فورک خودت پیدا یا ساخته می‌شود.</small></label>
        <label>ریپوی منبع<input id="sourceRepo" value="sabi-karami/SABIGOZAR"></label>
        <label>منطقه (Region)<select id="region"><option value="europe-west4-drams3a">EU West · Amsterdam (پیشنهادی ایران)</option><option value="us-east4-eqdc4a">US East</option><option value="us-west2">US West</option><option value="asia-southeast1-eqsg3a">Singapore</option></select></label>
        <label>IPهای تمیز Cloudflare<input id="cleanIps" value="104.16.1.1,172.67.1.1"><small>برای کانفیگ‌های ☁️ CDN. خالی = بدون CDN.</small></label>
        <label>اسم پروژه در Railway<input id="project" value="SABIGOZAR"></label>
        <label>اسم سرویس<input id="service" value="sabigozar"></label>
        <label>Workspace (خالی = اولین)<input id="workspace"></label>
        <label>کاربر تست نگه داشته شود<input id="testUser" placeholder="test1"><small>خالی: کاربر تست موقت ساخته و بعد از تست پاک می‌شود.</small></label>
        <label>رکوردهای DNS قدیمی برای پاک کردن<input id="deleteDns" placeholder="old.example.com"></label>
        <label>متغیرهای اضافه (هر خط KEY=VALUE)<textarea id="extraVars" placeholder="REALITY_SNI=www.microsoft.com"></textarea></label>
      </div>
      <div style="height:10px"></div>
      <label class="chk"><input type="checkbox" id="dnsOnly"> ابر خاکستری (بدون Proxy کلادفلر)</label>
      <label class="chk"><input type="checkbox" id="skipDeploy"> Deploy دوباره نکن (سرویس تازه‌ساخته خودش یک بار Deploy می‌شود)</label>
    </details>
    <div style="height:16px"></div>
    <button class="btn" id="goB">🚀 همه‌چیز را بساز و تنظیم کن</button>
  </div>

  <div class="card hide" id="progC">
    <h2>⏳ در حال انجام</h2>
    <div class="bar"><b id="barB"></b></div>
    <div class="steps" id="steps"></div>
    <div style="height:12px"></div>
    <div class="log" id="log"></div>
  </div>

  <div class="card hide" id="repC">
    <h2>📋 گزارش نصب</h2>
    <div class="rep" id="rep"></div>
    <div style="height:12px"></div>
    <div class="row"><button class="btn gh" id="dlR">⬇ دانلود گزارش</button><button class="btn gh" id="cpR">⧉ کپی گزارش</button><button class="btn gh" id="agB">↻ دوباره اجرا</button></div>
  </div>
  <div class="mut" style="text-align:center">SABIGOZAR · @SAHEBKARAMI</div>
</div>
<div class="toast" id="toast"></div>
<script src="/app.js"></script>
</body>
</html>
`;
