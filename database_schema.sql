CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT);
CREATE TABLE food_posts(id INTEGER PRIMARY KEY,provider_id INTEGER,title TEXT,quantity INTEGER,location TEXT,pickup_by TEXT,notes TEXT,status TEXT DEFAULT 'available',claimed_by INTEGER,created_at TEXT);
CREATE TABLE produce_listings(id INTEGER PRIMARY KEY,farmer_id INTEGER,vegetable TEXT,quantity REAL,unit TEXT,price REAL,location TEXT,contact_note TEXT,status TEXT DEFAULT 'available',buyer_id INTEGER,created_at TEXT);
