# personal_blog — Flask Portfolio App

Personal portfolio and blog for Kiran H L, built with Flask.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — add your Gmail App Password and SMTP_USER

# 3. Run (development)
python app.py

# 4. Open browser
# http://127.0.0.1:5000
```

## Project Structure

```
personal_blog/
├── app.py                  Main Flask application
├── requirements.txt        Python dependencies
├── .env.example            Secrets template (safe to commit)
├── .env                    Your actual secrets (NEVER commit)
├── .gitignore
├── README.md
├── templates/
│   └── personal_blog.html  Portfolio site (Jinja2 template)
└── static/
    └── contact_form.js     Contact form fetch handler
```

## Routes

| Method | Path              | Description                    |
|--------|-------------------|--------------------------------|
| GET    | /                 | Serves the portfolio homepage  |
| POST   | /submit-contact   | Handles contact form → email   |
| GET    | /health           | Health check                   |

## Contact Form Flow

```
Browser (personal_blog.html)
  → POST /submit-contact  (JSON)
    → Flask validates fields
      → SMTP STARTTLS → Gmail
        → Email delivered to kiranhl1709@gmail.com
```

## Production Deployment

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Set `ALLOWED_ORIGIN` in `.env` to your actual domain before deploying.

## Gmail App Password Setup

1. Enable 2-Step Verification on your Google account
2. Go to: https://myaccount.google.com/apppasswords
3. Create an app password named "personal_blog"
4. Copy the 16-character password into `SMTP_PASSWORD` in `.env`
