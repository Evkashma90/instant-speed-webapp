# Instant Speed Web App

وب‌اپ تخمین تندی لحظه‌ای جسم از روی ویدئو.

## اجرای محلی

```bash
pip install -r requirements.txt
streamlit run app.py
```

## انتشار روی Streamlit Community Cloud

1. فایل‌های این پوشه را داخل یک Repository در GitHub قرار بده.
2. وارد Streamlit Community Cloud شو.
3. Repository را انتخاب کن.
4. Main file path را روی `app.py` بگذار.
5. Deploy را بزن.

## محدودیت علمی
نسبت متر به پیکسل ثابت فرض می‌شود. اگر جسم به سمت دوربین نزدیک یا از آن دور شود، خطا بیشتر می‌شود.
