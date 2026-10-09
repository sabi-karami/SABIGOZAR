# 🛡 SABIGOZAR Deploy Panel

یک پنل وب روی **Cloudflare Workers** که با یک دکمه همه‌ی کارهای نصب را انجام می‌دهد و آخرش یک گزارش کامل می‌دهد.

## چه کارهایی انجام می‌دهد؟
| مرحله | کار |
|---|---|
| ۱ | بررسی توکن Railway، توکن Cloudflare، Zone دامنه، رمز ادمین و (اختیاری) توکن GitHub |
| ۲ | GitHub: Fork ریپو یا Sync فورک موجود با نسخه‌ی اصلی |
| ۳ | Railway: پروژه، سرویس از GitHub، متغیرها (`PUBLIC_DOMAIN`، `PORT`، `CLEAN_IPS`، `ADMIN_USERNAME`، `ADMIN_PASSWORD` قوی خودکار) |
| ۴ | Railway: Volume روی `/var/lib/sabigozar`، Health Check `/healthz`، Restart Always، Dockerfile، منطقه‌ی اروپا |
| ۵ | Railway: دامنه‌ی Railway (۸۰۸۰)، TCP Proxy برای Reality (۸۴۴۳)، دامنه‌ی شخصی |
| ۶ | Cloudflare: CNAME نارنجی، TXT تأیید، SSL Full، WebSockets، پاک کردن رکوردهای قدیمی |
| ۷ | Deploy آخرین نسخه |
| ۸ | صبر تا SUCCESS و گواهی SSL |
| ۹ | تست کامل: healthz از Cloudflare، ورود ادمین، کاربر تست، لینک ساب و صفحه‌ی ساب |
| ۱۰ | گزارش نهایی (کپی / دانلود) |

همه‌چیز **Idempotent** است: اجرای دوباره چیزی تکراری نمی‌سازد و فقط کمبودها را درست می‌کند.

## امنیت
- ورود به پنل با رمز `PANEL_PASSWORD` (Secret روی Worker).
- توکن‌ها فقط در همان درخواست به Railway / Cloudflare / GitHub فرستاده می‌شوند و هیچ‌جا ذخیره یا لاگ نمی‌شوند.

## نصب پنل روی Cloudflare
```bash
cd panel
# در wrangler.toml آدرس vpn.example.com را به دامنه‌ی خودت تغییر بده
npx wrangler deploy
npx wrangler secret put PANEL_PASSWORD
```
