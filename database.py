import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Create users table
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
''')

# Create sellers table
c.execute('''
CREATE TABLE IF NOT EXISTS sellers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    store_location TEXT,
    password TEXT NOT NULL,
    FOREIGN KEY(id) REFERENCES users(id)
)
''')

# Create products table
c.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    price INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    image TEXT NOT NULL,
    category TEXT,
    seller_id INTEGER,
    FOREIGN KEY (seller_id) REFERENCES sellers(id)
)
''')

# Create cart table
c.execute('''
CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id INTEGER NOT NULL,
    quantity INTEGER ,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create addresses table
c.execute('''
CREATE TABLE IF NOT EXISTS addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    address_line TEXT NOT NULL,
    city TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    state TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

# Create orders table with quantity
c.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,  -- ✅ Newly added column
    address TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Order Placed',
    order_id INTEGER UNIQUE,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
)
''')

# Add quantity column to orders table if it doesn't already exist (for safety)
try:
    c.execute("ALTER TABLE orders ADD COLUMN quantity INTEGER ")
except sqlite3.OperationalError:
    # The column likely already exists
    pass

# Insert logistics user (if not already present)
hashed_password = generate_password_hash('indianpost@123')
try:
    c.execute('''
        INSERT INTO users (name, email, phone, password, role)
        VALUES (?, ?, ?, ?, ?)
    ''', ('India Post', 'indianpost@gmail.com', '0000000000', hashed_password, 'logistics'))
except sqlite3.IntegrityError:
    print("Logistics user already exists.")

conn.commit()
conn.close()

print("Database initialized successfully.")
