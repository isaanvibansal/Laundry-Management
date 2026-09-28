-- Hostel Laundry Management System — Database Schema

DROP TABLE IF EXISTS order_status_log;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS vendors;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('student','admin','vendor')),
    hostel_block TEXT,
    room_number TEXT,
    phone TEXT,
    vendor_id INTEGER,               -- set only when role = 'vendor'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);

CREATE TABLE vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact_phone TEXT,
    address TEXT,
    price_per_kg REAL NOT NULL,
    turnaround_hours INTEGER DEFAULT 48,
    rating REAL DEFAULT 4.0,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    service_provider TEXT NOT NULL CHECK(service_provider IN ('inhouse','vendor')),
    vendor_id INTEGER,
    service_type TEXT NOT NULL CHECK(service_type IN ('wash_fold','wash_iron','dry_clean','iron_only')),
    is_subscription INTEGER DEFAULT 0,
    recurrence TEXT,                 -- 'weekly' | 'biweekly' | NULL
    items_description TEXT,
    weight_kg REAL,                  -- nullable: subscription orders confirm weight per pickup
    pickup_date TEXT NOT NULL,
    pickup_slot TEXT NOT NULL,
    delivery_date TEXT,
    status TEXT NOT NULL DEFAULT 'requested'
        CHECK(status IN ('requested','picked_up','in_progress','ready','delivered','cancelled')),
    estimated_cost REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);

CREATE TABLE order_status_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);
