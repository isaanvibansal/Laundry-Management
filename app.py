from functools import wraps
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

import db
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
db.init_app(app)

PRICE_TABLE = {
    "wash_fold": 30,
    "wash_iron": 40,
    "dry_clean": 80,
    "iron_only": 15,
}
SERVICE_LABELS = {
    "wash_fold": "Wash & Fold",
    "wash_iron": "Wash & Iron",
    "dry_clean": "Dry Clean",
    "iron_only": "Iron Only",
}
STATUS_LABELS = {
    "requested": "Requested",
    "picked_up": "Picked Up",
    "in_progress": "In Progress",
    "ready": "Ready",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}
STATUS_ORDER = ["requested", "picked_up", "in_progress", "ready", "delivered"]

app.jinja_env.globals.update(
    SERVICE_LABELS=SERVICE_LABELS,
    STATUS_LABELS=STATUS_LABELS,
    STATUS_ORDER=STATUS_ORDER,
)


# ---------------------------------------------------------------- helpers --
def login_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))
            if roles and session.get("role") not in roles:
                flash("You don't have access to that page.", "error")
                return redirect(url_for("dashboard_redirect"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def current_user():
    if "user_id" not in session:
        return None
    return db.get_db().execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()


app.jinja_env.globals["current_user"] = current_user


# -------------------------------------------------------------- landing --
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard_redirect"))
    return render_template("index.html")


@app.route("/dashboard")
@login_required()
def dashboard_redirect():
    role = session.get("role")
    if role == "student":
        return redirect(url_for("student_dashboard"))
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    if role == "vendor":
        return redirect(url_for("vendor_dashboard"))
    return redirect(url_for("index"))


# ------------------------------------------------------------------ auth --
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = db.get_db()
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        hostel_block = request.form.get("hostel_block", "").strip()
        room_number = request.form.get("room_number", "").strip()
        phone = request.form.get("phone", "").strip()

        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with that email already exists.", "error")
            return redirect(url_for("register"))

        conn.execute(
            """INSERT INTO users (name, email, password_hash, role, hostel_block, room_number, phone)
               VALUES (?, ?, ?, 'student', ?, ?, ?)""",
            (name, email, generate_password_hash(password), hostel_block, room_number, phone),
        )
        conn.commit()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = db.get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Incorrect email or password.", "error")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        flash(f"Welcome back, {user['name'].split()[0]}!", "success")
        return redirect(url_for("dashboard_redirect"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for("index"))


# --------------------------------------------------------------- student --
@app.route("/student/dashboard")
@login_required("student")
def student_dashboard():
    conn = db.get_db()
    uid = session["user_id"]
    orders = conn.execute(
        "SELECT * FROM orders WHERE student_id = ? ORDER BY created_at DESC LIMIT 5", (uid,)
    ).fetchall()
    stats = {
        "active": conn.execute(
            "SELECT COUNT(*) c FROM orders WHERE student_id=? AND status NOT IN ('delivered','cancelled')",
            (uid,),
        ).fetchone()["c"],
        "delivered": conn.execute(
            "SELECT COUNT(*) c FROM orders WHERE student_id=? AND status='delivered'", (uid,)
        ).fetchone()["c"],
        "total_spent": conn.execute(
            "SELECT COALESCE(SUM(estimated_cost),0) s FROM orders WHERE student_id=? AND status='delivered'",
            (uid,),
        ).fetchone()["s"],
    }
    return render_template("student/dashboard.html", orders=orders, stats=stats)


@app.route("/student/book", methods=["GET", "POST"])
@login_required("student")
def book_service():
    conn = db.get_db()
    vendors = conn.execute("SELECT * FROM vendors WHERE is_active=1").fetchall()

    if request.method == "POST":
        service_provider = request.form["service_provider"]
        vendor_id = request.form.get("vendor_id") or None
        service_type = request.form["service_type"]
        is_subscription = 1 if request.form.get("is_subscription") else 0
        recurrence = request.form.get("recurrence") if is_subscription else None
        items_description = request.form.get("items_description", "").strip()
        weight_raw = request.form.get("weight_kg", "").strip()
        weight_kg = float(weight_raw) if weight_raw and not is_subscription else (
            float(weight_raw) if weight_raw else None
        )
        pickup_date = request.form["pickup_date"]
        pickup_slot = request.form["pickup_slot"]
        notes = request.form.get("notes", "").strip()

        # cost estimate
        if service_provider == "inhouse":
            rate = PRICE_TABLE.get(service_type, 30)
            vendor_id = None
        else:
            vrow = conn.execute("SELECT price_per_kg FROM vendors WHERE id=?", (vendor_id,)).fetchone()
            rate = vrow["price_per_kg"] if vrow else 35
        estimated_cost = round(rate * weight_kg, 2) if weight_kg else None

        conn.execute(
            """INSERT INTO orders
               (student_id, service_provider, vendor_id, service_type, is_subscription, recurrence,
                items_description, weight_kg, pickup_date, pickup_slot, status, estimated_cost, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?, 'requested', ?, ?)""",
            (session["user_id"], service_provider, vendor_id, service_type, is_subscription, recurrence,
             items_description, weight_kg, pickup_date, pickup_slot, estimated_cost, notes),
        )
        conn.commit()
        new_id = conn.execute("SELECT last_insert_rowid() id").fetchone()["id"]
        conn.execute("INSERT INTO order_status_log (order_id, status) VALUES (?, 'requested')", (new_id,))
        conn.commit()

        flash("Laundry pickup booked successfully!", "success")
        return redirect(url_for("order_detail", order_id=new_id))

    return render_template(
        "student/book_service.html", vendors=vendors, today=date.today().isoformat(),
        price_table=PRICE_TABLE,
    )


@app.route("/student/orders")
@login_required("student")
def order_history():
    conn = db.get_db()
    status_filter = request.args.get("status", "all")
    query = "SELECT o.*, v.name as vendor_name FROM orders o LEFT JOIN vendors v ON o.vendor_id = v.id WHERE student_id=?"
    params = [session["user_id"]]
    if status_filter != "all":
        query += " AND status=?"
        params.append(status_filter)
    query += " ORDER BY created_at DESC"
    orders = conn.execute(query, params).fetchall()
    return render_template("student/order_history.html", orders=orders, status_filter=status_filter)


@app.route("/student/orders/<int:order_id>")
@login_required("student")
def order_detail(order_id):
    conn = db.get_db()
    order = conn.execute(
        "SELECT o.*, v.name as vendor_name, v.contact_phone as vendor_phone FROM orders o "
        "LEFT JOIN vendors v ON o.vendor_id = v.id WHERE o.id=? AND o.student_id=?",
        (order_id, session["user_id"]),
    ).fetchone()
    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("order_history"))
    log = conn.execute(
        "SELECT * FROM order_status_log WHERE order_id=? ORDER BY changed_at ASC", (order_id,)
    ).fetchall()
    return render_template("student/order_detail.html", order=order, log=log)


@app.route("/student/orders/<int:order_id>/cancel", methods=["POST"])
@login_required("student")
def cancel_order(order_id):
    conn = db.get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE id=? AND student_id=?", (order_id, session["user_id"])
    ).fetchone()
    if order and order["status"] in ("requested", "picked_up"):
        conn.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
        conn.execute("INSERT INTO order_status_log (order_id, status) VALUES (?, 'cancelled')", (order_id,))
        conn.commit()
        flash("Order cancelled.", "success")
    else:
        flash("This order can no longer be cancelled.", "error")
    return redirect(url_for("order_detail", order_id=order_id))


# ----------------------------------------------------------------- admin --
@app.route("/admin/dashboard")
@login_required("admin")
def admin_dashboard():
    conn = db.get_db()
    stats = {
        "total_orders": conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"],
        "active_inhouse": conn.execute(
            "SELECT COUNT(*) c FROM orders WHERE service_provider='inhouse' AND status NOT IN ('delivered','cancelled')"
        ).fetchone()["c"],
        "delivered_today": conn.execute(
            "SELECT COUNT(*) c FROM orders WHERE status='delivered' AND date(delivery_date)=date('now')"
        ).fetchone()["c"],
        "total_students": conn.execute("SELECT COUNT(*) c FROM users WHERE role='student'").fetchone()["c"],
    }
    recent = conn.execute(
        "SELECT o.*, u.name as student_name, v.name as vendor_name FROM orders o "
        "JOIN users u ON o.student_id=u.id LEFT JOIN vendors v ON o.vendor_id=v.id "
        "ORDER BY o.created_at DESC LIMIT 8"
    ).fetchall()
    return render_template("admin/dashboard.html", stats=stats, recent=recent)


@app.route("/admin/orders")
@login_required("admin")
def admin_orders():
    conn = db.get_db()
    provider_filter = request.args.get("provider", "all")
    status_filter = request.args.get("status", "all")
    query = ("SELECT o.*, u.name as student_name, u.room_number, u.hostel_block, v.name as vendor_name "
              "FROM orders o JOIN users u ON o.student_id=u.id LEFT JOIN vendors v ON o.vendor_id=v.id WHERE 1=1")
    params = []
    if provider_filter != "all":
        query += " AND service_provider=?"
        params.append(provider_filter)
    if status_filter != "all":
        query += " AND status=?"
        params.append(status_filter)
    query += " ORDER BY o.created_at DESC"
    orders = conn.execute(query, params).fetchall()
    return render_template(
        "admin/orders.html", orders=orders, provider_filter=provider_filter, status_filter=status_filter
    )


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@login_required("admin", "vendor")
def update_order_status(order_id):
    new_status = request.form["status"]
    conn = db.get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()

    if order is None:
        flash("Order not found.", "error")
        return redirect(request.referrer or url_for("index"))

    # vendors may only touch their own orders
    if session["role"] == "vendor":
        me = current_user()
        if order["vendor_id"] != me["vendor_id"]:
            flash("You can only update your own orders.", "error")
            return redirect(url_for("vendor_dashboard"))

    delivery_date = date.today().isoformat() if new_status == "delivered" else order["delivery_date"]
    conn.execute("UPDATE orders SET status=?, delivery_date=? WHERE id=?", (new_status, delivery_date, order_id))
    conn.execute("INSERT INTO order_status_log (order_id, status) VALUES (?, ?)", (order_id, new_status))
    conn.commit()
    flash(f"Order #{order_id} marked as {STATUS_LABELS.get(new_status, new_status)}.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/admin/vendors")
@login_required("admin")
def admin_vendors():
    conn = db.get_db()
    vendors = conn.execute(
        "SELECT v.*, (SELECT COUNT(*) FROM orders o WHERE o.vendor_id=v.id) as order_count "
        "FROM vendors v ORDER BY v.name"
    ).fetchall()
    return render_template("admin/vendors.html", vendors=vendors)


@app.route("/admin/vendors/add", methods=["POST"])
@login_required("admin")
def add_vendor():
    conn = db.get_db()
    conn.execute(
        """INSERT INTO vendors (name, contact_phone, address, price_per_kg, turnaround_hours, rating)
           VALUES (?, ?, ?, ?, ?, 4.0)""",
        (
            request.form["name"].strip(),
            request.form.get("contact_phone", "").strip(),
            request.form.get("address", "").strip(),
            float(request.form["price_per_kg"]),
            int(request.form.get("turnaround_hours", 48)),
        ),
    )
    conn.commit()
    flash("Vendor added.", "success")
    return redirect(url_for("admin_vendors"))


@app.route("/admin/vendors/<int:vendor_id>/toggle", methods=["POST"])
@login_required("admin")
def toggle_vendor(vendor_id):
    conn = db.get_db()
    v = conn.execute("SELECT is_active FROM vendors WHERE id=?", (vendor_id,)).fetchone()
    if v:
        conn.execute("UPDATE vendors SET is_active=? WHERE id=?", (0 if v["is_active"] else 1, vendor_id))
        conn.commit()
    return redirect(url_for("admin_vendors"))


# ---------------------------------------------------------------- vendor --
@app.route("/vendor/dashboard")
@login_required("vendor")
def vendor_dashboard():
    conn = db.get_db()
    me = current_user()
    orders = conn.execute(
        "SELECT o.*, u.name as student_name, u.room_number, u.hostel_block FROM orders o "
        "JOIN users u ON o.student_id=u.id WHERE o.vendor_id=? ORDER BY o.created_at DESC",
        (me["vendor_id"],),
    ).fetchall()
    stats = {
        "pending": len([o for o in orders if o["status"] not in ("delivered", "cancelled")]),
        "delivered": len([o for o in orders if o["status"] == "delivered"]),
        "total": len(orders),
    }
    vendor = conn.execute("SELECT * FROM vendors WHERE id=?", (me["vendor_id"],)).fetchone()
    return render_template("vendor/dashboard.html", orders=orders, stats=stats, vendor=vendor)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
