# 📝 تغییرات SABIGOZAR

## v1.1.0
- **جدید:** اسکریپت `tools/deploy.py` برای نصب کامل با یک دستور روی Railway پشت Cloudflare: پروژه، سرویس، Volume، Health Check، Restart Policy، منطقه‌ی اروپا، دامنه‌ی Railway، TCP Proxy برای Reality، دامنه‌ی شخصی، رکوردهای CNAME (Proxied) و TXT، SSL Full، WebSockets، Redeploy و تست کامل (ورود، کاربر تست، لینک اشتراک)
- **جدید:** راهنمای کامل فارسی نصب خودکار و دستی: `docs/DEPLOY-AUTOMATION.md`
- **رفع مشکل:** Railway فایل `railway.json` را برای سرویس‌های جدید اعمال نمی‌کند، پس Health Check خاموش بود و Restart Policy روی `ON_FAILURE` می‌ماند. حالا اسکریپت این‌ها را از API می‌گذارد و README قدم دستی آن را دارد.
- **README:** بخش Cloudflare کامل شد (رکورد TXT تأیید، SSL Full، WebSockets، خطای `Not available`)، پیشنهاد منطقه‌ی EU West، ردیف‌های جدید رفع خطا و سؤال «چرا رمز در Variables نیست؟»
- **CI:** بررسی اجرای `tools/deploy.py --help`


## v1.0.0
- اولین نسخه‌ی SABIGOZAR بر پایه‌ی PasarGuard v5.4.1، نود v0.5.4 و Xray 26.3.27
- برند کامل SABIGOZAR در داشبورد، ترجمه‌ها، لوگوها، API و ربات. تبلیغات و پنجره‌ی کمک مالی حذف شد.
- رمز مالک تصادفی و قوی، بازیابی رمز با `ADMIN_PASSWORD`، و حذف حساب‌های پیش‌فرض
- ۸ کانفیگ: Reality-Vision (TCP Proxy)، VLESS-WS، VLESS-HTTPUpgrade، VLESS-XHTTP، Trojan-WS، VMess-WS، Trojan-HTTPUpgrade، VLESS-WS Fragment، به‌علاوه‌ی CDN اختیاری
- مسیرها و کلید Reality جداگانه برای هر نصب
- نقش نماینده و ۸ قالب فروش
- ربات تلگرام، اعلان‌ها، بکاپ خودکار به تلگرام و Watchdog
- صفحه‌ی اشتراک فارسی با تاریخ شمسی، QR داخلی، تست پینگ و اتصال یک‌لمسی با ۹ برنامه
- تست خودکار GitHub Actions با پنل، Xray و nginx واقعی
