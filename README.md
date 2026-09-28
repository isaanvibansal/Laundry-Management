# MUJ Hostel Laundry Management System

A working Flask + SQLite web app for the SE Lab project — students book laundry
pickups (in-house or external vendor), admins run the operations desk, and
vendors manage the orders routed to them.

## Folder structure

```
laundry_management_system/
├── app.py                  # Flask routes / app logic
├── db.py                   # SQLite connection helper
├── init_db.py               # Creates + seeds laundry.db
├── schema.sql                # Table definitions
├── requirements.txt
├── static/
│   └── css/style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── student/  (dashboard, book_service, order_history, order_detail)
    ├── admin/    (dashboard, orders, vendors)
    └── vendor/   (dashboard)
```

## Run it locally (VS Code)

```bash
cd laundry_management_system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python init_db.py               # creates laundry.db with demo data
python app.py                   # http://127.0.0.1:5000
```

### Demo logins
| Role    | Email                          | Password   |
|---------|---------------------------------|-----------|
| Student | riya.sharma@muj.manipal.edu     | student123 |
| Student | aman.verma@muj.manipal.edu      | student123 |
| Admin   | admin@muj.manipal.edu           | admin123   |
| Vendor  | vendor1@laundry.com             | vendor123  |

Run `python init_db.py` again any time to reset the database.

## Deployment (Render — free tier)

1. Push this folder to a GitHub repo.
2. Add a `Procfile` with: `web: gunicorn app:app`
3. Add `gunicorn` to `requirements.txt`.
4. On render.com → New → Web Service → connect the repo.
   - Build command: `pip install -r requirements.txt && python init_db.py`
   - Start command: `gunicorn app:app`
5. Deploy. Render gives you a live `https://your-app.onrender.com` URL.

Note: Render's free tier filesystem resets on redeploy, so `laundry.db`
resets too — fine for a lab demo, not for production data.
