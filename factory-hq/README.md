# 🏭 CYRUS TEAM — Factory HQ v1.0

کارخونه ایجنت واقعی — نه ویترین. هر ایجنت یه ماژول پایتونه که واقعاً کار می‌کنه، و هیچ‌چیز بدون تأیید تو (Approve) اجرا نمی‌شه.

## ایجنت‌ها (واقعی)
| ایجنت | دپارتمان | چیکار می‌کنه |
|---|---|---|
| Bug Hunter | ENGINEERING | چک زنده: صفحه اپ، نسخه sw.js، سایت اصلی، سکشن‌های فایل دانش |
| Content Writer | CONTENT | پیش‌نویس پک Shorts (تیتر/توضیحات/هشتگ) برای تأیید |
| Knowledge Improver | BRAIN | بررسی فایل دانش: سکشن‌های A تا N + کلمات کلیدی قوانین سخت |

## اجرا روی لپ‌تاپ
```bash
cd factory
python3 -m venv venv
./venv/bin/pip install flask   # ویندوز: venv\Scripts\pip install flask
./venv/bin/python app.py       # ویندوز: venv\Scripts\python app.py
```
بعد باز کن: http://localhost:5050

## داشبورد HQ
- 🗺️ کارت دپارتمان‌ها + ایجنت‌ها (دکمه ▶ Run)
- ✅ صف تأیید (Approval Queue): هر پیشنهاد ایجنت اینجاست — Approve یا Reject با یه کلیک
- 📝 لاگ فعالیت‌ها (هر ۱۵ ثانیه تازه می‌شه)

الان یه آیتم واقعی توی صف تأییده: **فیکس زوم آیفون** (خط ۵۸، ۱۴px به ۱۶px).

## API
- `GET /api/status` — وضعیت کارخونه (مثل همون JSON ورسل)
- `GET /api/agents` — لیست ایجنت‌ها
- `POST /api/run/<agent_id>` — اجرای ایجنت (برای content_writer می‌تونی topic بفرستی)
- `GET /api/approvals` — صف تأیید
- `POST /api/approvals/<id>/approve` یا `/reject`

## قدم‌های بعدی (باهم تصمیم می‌گیریم)
1. ایجنت‌های بیشتر (ترید؟ ویدیو؟ پشتیبانی مشتری؟)
2. زمان‌بندی خودکار (هر X ساعت یه ایجنت خودش اجرا بشه)
3. اجرای دائمی: سرور مجازی (VPS) یا همین لپ‌تاپ
4. اتصال به GitHub/Vercel که الان داری می‌سازی
