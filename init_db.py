"""
Run this once (and any time you want a fresh database) to build laundry.db
and seed it with demo accounts + sample data.

    python init_db.py
"""
import sqlite3
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

DATABASE = "laundry.db"


def run():
    conn = sqlite3.connect(DATABASE)
    conn.executescript(open("schema.sql").read())

    cur = conn.cursor()

    # ---------- Vendors ----------
    vendors = [
        ("QuickWash Laundry Co.", "+91 98290 11122", "Near MUJ Gate No. 1, Jaipur-Ajmer Expy", 35.0, 24, 4.6),
        ("Sparkle Dry Cleaners", "+91 98290 33445", "Bagru Road, opp. MUJ Bus Stand", 45.0, 48, 4.3),
        ("FreshFold Express", "+91 98290 55667", "Dehmi Kalan, near MUJ Campus", 30.0, 36, 4.1),
    ]
    cur.executemany(
        """INSERT INTO vendors (name, contact_phone, address, price_per_kg, turnaround_hours, rating)
           VALUES (?, ?, ?, ?, ?, ?)""",
        vendors,
    )

    # ---------- Users ----------
    users = [
        ("Hostel Laundry Admin", "admin@muj.manipal.edu", "admin123", "admin", None, None, "0141-2999100", None),
        ("Riya Sharma", "riya.sharma@muj.manipal.edu", "student123", "student", "Yamuna Hostel", "B-214", "9876500001", None),
        ("Aman Verma", "aman.verma@muj.manipal.edu", "student123", "student", "Ganga Hostel", "C-108", "9876500002", None),
        ("QuickWash Operator", "vendor1@laundry.com", "vendor123", "vendor", None, None, "9829011122", 1),
    ]
    for name, email, pw, role, block, room, phone, vendor_id in users:
        cur.execute(
            """INSERT INTO users (name, email, password_hash, role, hostel_block, room_number, phone, vendor_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, email, generate_password_hash(pw), role, block, room, phone, vendor_id),
        )

    # ---------- Sample orders (for a non-empty demo) ----------
    today = date.today()
    orders = [
        # student_id, service_provider, vendor_id, service_type, is_subscription, recurrence,
        # items, weight, pickup_date, pickup_slot, delivery_date, status, cost, notes
        (2, "inhouse", None, "wash_fold", 0, None, "3 shirts, 2 jeans, bedsheet", 4.5,
         str(today - timedelta(days=5)), "Morning (8-10 AM)", str(today - timedelta(days=3)),
         "delivered", 135.0, "Fold, no starch"),
        (2, "vendor", 1, "dry_clean", 0, None, "1 blazer, 1 formal trouser", 2.0,
         str(today - timedelta(days=2)), "Evening (5-7 PM)", None,
         "in_progress", 90.0, "Needed before placement interview"),
        (3, "inhouse", None, "wash_iron", 1, "weekly", "Weekly hostel laundry bag", None,
         str(today + timedelta(days=1)), "Morning (8-10 AM)", None,
         "requested", None, "Standard weekly subscription"),
        (3, "vendor", 1, "wash_fold", 0, None, "Gym kit + 4 t-shirts", 3.0,
         str(today - timedelta(days=1)), "Afternoon (1-3 PM)", None,
         "picked_up", 105.0, None),
    ]
    cur.executemany(
        """INSERT INTO orders
           (student_id, service_provider, vendor_id, service_type, is_subscription, recurrence,
            items_description, weight_kg, pickup_date, pickup_slot, delivery_date, status,
            estimated_cost, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        orders,
    )

    for oid in range(1, len(orders) + 1):
        cur.execute(
            "INSERT INTO order_status_log (order_id, status) VALUES (?, ?)",
            (oid, orders[oid - 1][11]),
        )

    conn.commit()
    conn.close()
    print("laundry.db created and seeded.")
    print("\nDemo logins:")
    print("  Admin   -> admin@muj.manipal.edu / admin123")
    print("  Student -> riya.sharma@muj.manipal.edu / student123")
    print("  Student -> aman.verma@muj.manipal.edu / student123")
    print("  Vendor  -> vendor1@laundry.com / vendor123")


if __name__ == "__main__":
    run()
