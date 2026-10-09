# ⚡ نصب خودکار روی Railway پشت Cloudflare

این راهنما **همه‌ی** کارهایی را که برای بالا آوردن SABIGOZAR روی Railway، پشت Cloudflare و روی دامنه‌ی شخصی لازم است، قدم‌به‌قدم ثبت می‌کند.
همه‌ی این قدم‌ها روی یک نصب واقعی انجام و تست شده‌اند.

دو راه داری:
- **راه ۱ (پیشنهادی):** اسکریپت [`tools/deploy.py`](../tools/deploy.py) با یک دستور همه‌چیز را می‌سازد و تست می‌کند.
- **راه ۲:** همان قدم‌ها را دستی در پنل Railway و Cloudflare انجام بده (بخش پایین).

> ⚠️ قوانین Railway اجرای پروکسی و فروش دوباره‌ی منابع را ممنوع کرده. بخش «قبل از نصب حتماً بخوان» در [README](../README.md) را بخوان و در Railway سقف هزینه (Usage Limit) بگذار.

---

## ۱) پیش‌نیازها

| چیز | توضیح |
|---|---|
| ریپو در GitHub | این ریپو یا Fork آن در اکانت خودت. اپ GitHub مال Railway باید به آن دسترسی داشته باشد. |
| دامنه روی Cloudflare | دامنه (Zone) باید در Cloudflare فعال (Active) باشد. پنل روی یک ساب‌دامین می‌نشیند، مثلاً `panel.example.com`. |
| توکن Railway | از [railway.com/account/tokens](https://railway.com/account/tokens) یک توکن اکانت یا Workspace بساز (نه Project Token). |
| توکن Cloudflare | در **My Profile ← API Tokens** یک توکن بساز با دسترسی‌های: `Zone:Read`، `DNS:Edit`، `Zone Settings:Edit` فقط برای همان دامنه. |
| Python 3.8+ | فقط کتابخانه‌ی استاندارد؛ نصب چیز دیگری لازم نیست. |

> 🔒 توکن‌ها را **هرگز** در GitHub، چت یا فایل نگذار. فقط در متغیر محیطی ترمینال خودت. اگر جایی لو رفت، همان لحظه باطلش کن.

---

## ۲) نصب با یک دستور

```bash
git clone https://github.com/YOUR_USER/SABIGOZAR && cd SABIGOZAR
export RAILWAY_TOKEN="..."          # توکن Railway
export CLOUDFLARE_API_TOKEN="..."   # توکن Cloudflare

python3 tools/deploy.py \
  --repo YOUR_USER/SABIGOZAR \
  --domain panel.example.com \
  --clean-ips 104.16.1.1,172.67.1.1
```

گزینه‌های مهم:

| گزینه | کار |
|---|---|
| `--region` | منطقه‌ی سرور. پیش‌فرض `europe-west4-drams3a` (هلند) که از ایران پینگ بهتری دارد. |
| `--clean-ips` | IPهای تمیز Cloudflare برای ساخت کانفیگ‌های ☁️ CDN. |
| `--var KEY=VALUE` | هر متغیر دیگر (مثل `REALITY_SNI=www.microsoft.com`). برای رمز و توکن، مستقیم در Variables خود Railway بگذار. |
| `--delete-dns NAME` | پاک کردن رکوردهای قدیمی یک اسم (مثلاً ساب‌دامینی که به پروژه‌ی پاک‌شده‌ی Railway اشاره می‌کند). |
| `--test-user NAME` | یک کاربر با قالب «تست ۱ گیگ یک‌روزه» می‌سازد، نگه می‌دارد و لینک اشتراکش را چاپ می‌کند. |
| `--no-redeploy` | فقط بررسی و تکمیل تنظیمات، بدون Redeploy. برای چکاپ یک نصب موجود عالی است. |
| `--dns-only` | ابر خاکستری (بدون Proxy کلادفلر). |

اسکریپت **Idempotent** است: اگر دوباره اجرایش کنی، چیزی تکراری ساخته نمی‌شود؛ فقط کمبودها را درست می‌کند و دوباره تست می‌گیرد.

خروجی نمونه (از نصب واقعی):

```
[deploy] project SABIGOZAR: exists
[deploy] volume /var/lib/sabigozar: exists
[deploy] service settings: healthcheck /healthz (300s), restart ALWAYS, Dockerfile
[deploy] region: europe-west4-drams3a
[deploy] TCP Proxy (Reality): xxx.proxy.rlwy.net:12345
[deploy] cloudflare: CNAME panel.example.com: ok
[deploy] cloudflare: TXT _railway-verify.panel.example.com: ok
[deploy] cloudflare: ssl = full: ok
[deploy] cloudflare: websockets = on: ok
[deploy] panel.example.com: verified, certificate valid
[deploy] 10 configs ready on panel.example.com + Reality on xxx.proxy.rlwy.net:12345
[deploy] healthz: 200 (served by cloudflare)
[deploy] owner login: ok
[deploy] subscription: 10 configs
[deploy] temporary user deploycheck12345 removed
```

---

## ۳) اسکریپت دقیقاً چه کارهایی می‌کند؟ (همان راه دستی)

اگر نمی‌خواهی اسکریپت اجرا کنی، همین قدم‌ها را به همین ترتیب دستی انجام بده.

### الف) Railway

| # | کار | در پنل Railway |
|---|---|---|
| 1 | ساخت پروژه `SABIGOZAR` | **New Project** |
| 2 | ساخت سرویس `sabigozar` از ریپوی GitHub | **Deploy from GitHub repo** |
| 3 | متغیرها: `PUBLIC_DOMAIN=panel.example.com`، `PORT=8080` و (اختیاری) `CLEAN_IPS` | **Variables** |
| 4 | Volume روی مسیر `/var/lib/sabigozar` | کلیک راست روی سرویس ← **Attach Volume** |
| 5 | Healthcheck Path = `/healthz`، Timeout = `300` | **Settings ← Deploy** |
| 6 | Restart Policy = **Always** | **Settings ← Deploy** |
| 7 | Dockerfile Path = `Dockerfile` | **Settings ← Build** |
| 8 | Region = **EU West (Amsterdam)** | **Settings ← Deploy ← Regions** |
| 9 | دامنه‌ی Railway با پورت `8080` | **Settings ← Networking ← Generate Domain** |
| 10 | TCP Proxy با پورت `8443` (برای Reality) | **Settings ← Networking ← TCP Proxy** |
| 11 | دامنه‌ی شخصی `panel.example.com` با پورت `8080` | **Settings ← Networking ← Custom Domain** |

> **چرا قدم ۵ تا ۷ لازم است؟** Railway دیگر فایل `railway.json` را برای سرویس‌های جدید اعمال نمی‌کند (Config as Code منسوخ شده). در نصب واقعی، بدون این قدم‌ها Health Check خاموش بود و Restart Policy روی `ON_FAILURE` (حداکثر ۱۰ بار) مانده بود؛ یعنی اگر ۱۰ بار پشت سر هم کرش کند، سرویس دیگر بالا نمی‌آید.

بعد از قدم ۱۱، Railway دو رکورد بهت می‌دهد:

| نوع | اسم | مقدار |
|---|---|---|
| CNAME | `panel` | یک آدرس اختصاصی مثل `abcd1234.up.railway.app` (این **با دامنه‌ی Generate‌شده‌ی سرویس فرق دارد**) |
| TXT | `_railway-verify.panel` | `railway-verify=...` |

### ب) Cloudflare

| # | کار | در پنل Cloudflare |
|---|---|---|
| 1 | رکورد CNAME بالا با **Proxy status: Proxied (ابر نارنجی)** | **DNS ← Records ← Add record** |
| 2 | رکورد TXT بالا | **DNS ← Records ← Add record** |
| 3 | اگر برای همین اسم رکورد A / AAAA / CNAME قدیمی هست، پاکش کن | **DNS ← Records** |
| 4 | SSL/TLS روی **Full** (نه Flexible) | **SSL/TLS ← Overview** |
| 5 | WebSockets روشن | **Network ← WebSockets** |
| 6 | رکوردهای قدیمی که به پروژه‌های پاک‌شده‌ی Railway اشاره می‌کنند را پاک کن | **DNS ← Records** |

### پ) بعد از DNS
1. در Railway یک بار **Redeploy** بزن.
2. چند دقیقه صبر کن تا در **Networking** کنار دامنه تیک سبز بیاید (تأیید + گواهی).
3. در لاگ باید این خط را ببینی: `N configs ready on panel.example.com + Reality on xxx.proxy.rlwy.net:12345`

### ت) تست نهایی
1. `https://panel.example.com/healthz` باید `ok` بدهد و در هدر پاسخ `server: cloudflare` باشد.
2. وارد `https://panel.example.com/dashboard/` شو (نام کاربری و رمز در لاگ Deploy).
3. یک کاربر از قالب **تست · 1GB · 1 روز** بساز، چند ثانیه صبر کن تا گروه کانفیگ‌ها خودکار وصل شود.
4. لینک اشتراک را در v2rayNG / Hiddify / Happ اضافه کن. باید ۸ کانفیگ (یا ۸ + تعداد IPهای تمیز) ببینی.

---

## ۴) نکته‌ها و مشکلاتی که در نصب واقعی پیدا شد

| مشکل | علت و راه‌حل |
|---|---|
| Custom Domain: `Failed to create custom domain` یا `Not available` | این دامنه هنوز به یک پروژه‌ی دیگر Railway (قدیمی یا اکانت دیگر) وصل است. آنجا پاکش کن یا یک ساب‌دامین دیگر بگذار. اسکریپت قبل از ساخت، این را با `customDomainAvailable` چک می‌کند. |
| Health Check و Restart Policy از `railway.json` اعمال نشد | Config as Code برای سرویس‌های جدید کار نمی‌کند. این تنظیمات را دستی (قدم ۵ تا ۷) یا با اسکریپت بگذار. |
| رمز پنل در Variables نیست | طبیعی است. Variables فقط ورودی هستند. رمز تصادفی روی Volume ذخیره و در لاگ Deploy چاپ می‌شود. اگر می‌خواهی در Variables باشد، `ADMIN_PASSWORD` را بگذار و Redeploy کن. |
| `Free plan resource provision limit exceeded` | سقف منابع پلن رایگان/Trial پر شده. پروژه‌های بلااستفاده را پاک کن یا پلن را ارتقا بده. |
| پروژه‌ی موجود از API پیدا نمی‌شود | در API باید پروژه‌ها را با `workspaceId` گرفت؛ بدون آن فهرست خالی برمی‌گردد. اسکریپت این را رعایت می‌کند. |
| `ERR_TOO_MANY_REDIRECTS` یا خطای 525 پشت Cloudflare | SSL/TLS را روی **Full** بگذار. |
| کانفیگ‌های WS پشت Cloudflare وصل نمی‌شوند | **Network ← WebSockets** را روشن کن. |
| Reality از راه دامنه‌ی Cloudflare وصل نمی‌شود | طبیعی است. Reality مستقیم از TCP Proxy خود Railway (`xxx.proxy.rlwy.net:پورت`) وصل می‌شود؛ Cloudflare فقط ترافیک وب را جابه‌جا می‌کند. |
| کانفیگ‌های ☁️ CDN کندند یا وصل نمی‌شوند | IPهای تمیز به اپراتور تو بستگی دارند. با یک اسکنر IP تمیز (مثلاً داخل Hiddify) IP بهتر پیدا کن و `CLEAN_IPS` را عوض کن. |
| منطقه‌ی پیش‌فرض Railway آمریکاست | برای کاربران ایران **EU West** را انتخاب کن. Volume هم با سرویس منتقل می‌شود. |

---

## ۵) امنیت

- لینک اشتراک هر کاربر مثل رمز است. فقط به خود همان کاربر بده.
- آدرس `/dashboard/` را عمومی منتشر نکن. در این ریپو هم همه‌جا از `panel.example.com` استفاده شده.
- توکن Railway و Cloudflare را با کمترین دسترسی لازم بساز و بعد از نصب اگر لازمشان نداری پاکشان کن.
- اسکریپت رمز پنل را از لاگ می‌خواند فقط برای تست لاگین، و هیچ‌جا چاپش نمی‌کند.
