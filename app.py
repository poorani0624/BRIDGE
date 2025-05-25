from flask import Flask, render_template, request, redirect, session, url_for, flash,jsonify
from flask_login import login_required, current_user
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from contextlib import closing
from datetime import datetime, timedelta
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict


app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')

# Function to get a database connection
def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row  # To return rows as dictionaries
    return conn

# User Model (Buyers)
def get_user_by_email(email):
    with closing(get_db()) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
    return user

# Seller Model
def get_seller_by_email(email):
    with closing(get_db()) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM sellers WHERE email = ?", (email,))
        seller = c.fetchone()
    return seller

# Create DB and tables (Use your existing init_db() function here if needed)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with closing(get_db()) as conn:
        products = conn.execute("SELECT * FROM products").fetchall()

    # Group products by category
    products_by_category = defaultdict(list)
    for p in products:
        category = p['category'] if p['category'] else 'Uncategorized'
        products_by_category[category].append(p)

    return render_template('dashboard.html', products_by_category=products_by_category)

@app.route('/product/<int:product_id>')
def product_view(product_id):
    with closing(get_db()) as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if not product:
        flash('Product not found.', 'warning')
        return redirect(url_for('dashboard'))

    return render_template('product_view.html', product=product)

# Function to send OTP email
def send_otp_email(email, otp):
    sender_email = "connectbridge2us@gmail.com"
    receiver_email = email
    password = "jeqp jebn xtle eudq"  # Make sure the password is correct
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = 'Your OTP Code'

    body = f"Your OTP code is: {otp}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:  # Use Gmail's SMTP server
            server.starttls()
            server.login(sender_email, password)
            print(f"Sending OTP to {email}")  # Debug print
            text = msg.as_string()
            server.sendmail(sender_email, receiver_email, text)
            print(f"Email sent successfully to {email}")  # Debug print
    except Exception as e:
        raise Exception("Error sending OTP email") from e  # ⬅️ Raise exception to handle outside

def insert_user(name, email, phone, password):
    conn = sqlite3.connect('users.db')  # Ensure the correct database is used
    c = conn.cursor()

    # Check if the email already exists
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    existing_user = c.fetchone()

    if existing_user:
        # Email already exists, handle the error (e.g., prompt user to log in)
        conn.close()
        raise ValueError("This email is already registered. Please log in.")
    
    # Proceed to insert the new user
    c.execute('''
        INSERT INTO users (name, email, phone, password, role)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, email, phone, password, 'buyer'))  # Default role as 'buyer'
    
    conn.commit()
    conn.close()


import re  # at the top if not already imported

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if not re.fullmatch(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            flash('Password must be at least 8 characters long and include a letter, a number, and a special character.', 'danger')
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))
        
        # Backend phone validation
        if not re.fullmatch(r'\d{10}', phone):
            flash('Phone number must be exactly 10 digits.', 'danger')
            return redirect(url_for('signup'))
        if not re.fullmatch(r'[A-Za-z ]+', name):
            flash('Name must contain only letters and spaces.', 'danger')
            return redirect(url_for('signup'))

        if password == confirm_password:
            otp = random.randint(100000, 999999)
            session['otp'] = otp
            session['email'] = email
            session['name'] = name
            session['phone'] = phone
            session['password'] = generate_password_hash(password)

            send_otp_email(email, otp)
            return redirect(url_for('otp'))
        else:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

    return render_template('signup.html')
@app.route('/otp', methods=['GET', 'POST'])
def otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp', '')  # Get the full 6-digit OTP from the single input
        
        if entered_otp == str(session.get('otp')):
            # OTP is correct, retrieve signup info from session
            name = session.get('name')
            email = session.get('email')
            phone = session.get('phone')
            password = session.get('password')

            try:
                insert_user(name, email, phone, password)
            except ValueError as e:
                flash(str(e), 'danger')
                return redirect(url_for('signup'))

            # Clear session data after successful signup
            for key in ['otp', 'email', 'name', 'phone', 'password']:
                session.pop(key, None)

            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP. Please try again.', 'danger')

    return render_template('otp.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']

            # Role-based redirection
            if user['role'] == 'logistics':
                return redirect(url_for('logistics_dashboard'))
            elif user['role'] == 'seller':
                return redirect(url_for('add_item'))  # Redirect sellers to add_item page
            else:
                return redirect(url_for('dashboard'))  # Buyers go to dashboard
        else:
            flash('Invalid login credentials.', 'danger')

    return render_template('login.html')

@app.route('/logistics')
def logistics_placeholder():
    return "<h2>Welcome, Logistics User! Dashboard under construction.</h2>"

@app.route('/logistics_dashboard')
def logistics_dashboard():
    if 'user_id' not in session or session.get('role') != 'logistics':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT o.order_id, o.address, o.status, o.product_id, o.user_id,
               o.quantity,  -- ✅ Fetch quantity from orders table
               p.name, p.image
        FROM orders o
        JOIN products p ON o.product_id = p.id
    ''')
    orders = c.fetchall()
    conn.close()

    return render_template('logistics_dashboard.html', orders=orders)

def insert_seller(name, email, phone, password, store_location):
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        
        # Check if email exists in users
        c.execute('SELECT id FROM users WHERE email = ?', (email,))
        if c.fetchone():
            raise ValueError("Email already registered as a user or seller")
        
        # Optional: Check sellers again
        c.execute('SELECT id FROM sellers WHERE email = ?', (email,))
        if c.fetchone():
            raise ValueError("Email already registered as a seller")
        
        # Insert into users
        c.execute('''INSERT INTO users (name, email, phone, password, role) VALUES (?, ?, ?, ?, ?)''',
                  (name, email, phone, password, 'seller'))
        user_id = c.lastrowid
        
        # Insert into sellers with category
        c.execute('''INSERT INTO sellers (id, name, email, phone, store_location, password)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (user_id, name, email, phone, store_location, password))

@app.route('/seller_signup', methods=['GET', 'POST'])
def seller_signup():
    if request.method == 'POST':
        name = request.form.get('seller_name')
        email = request.form.get('email')

        country_code = request.form.get('country_code')
        phone = request.form.get('phone')
        full_phone = f"{country_code}{phone}"

        store_location = request.form.get('store_location')

        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not re.fullmatch(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            flash('Password must be at least 8 characters long and include a letter, a number, and a special character.', 'danger')
            return redirect(url_for('seller_signup'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('seller_signup'))
        
        if not re.fullmatch(r'[A-Za-z ]+', name):
            flash('Name must contain only letters and spaces.', 'danger')
            return redirect(url_for('seller_signup'))

        if not re.fullmatch(r'[A-Za-z ]+', store_location):
            flash('Location must contain only letters and spaces.', 'danger')
            return redirect(url_for('seller_signup'))
        
        if not re.fullmatch(r'\d{10}', phone):
            flash('Phone number must be exactly 10 digits.', 'danger')
            return redirect(url_for('seller_signup'))
        
        otp = random.randint(100000, 999999)
        session['otp'] = otp
        session['email'] = email
        session['name'] = name
        session['phone'] = full_phone
        session['store_location'] = store_location
        session['password'] = generate_password_hash(password)
        
        try:
            send_otp_email(email, otp)
        except Exception as e:
            flash("There was an error sending the OTP. Please try again later.", 'danger')
            return redirect(url_for('seller_otp'))  # ✅ Now redirects to OTP page with error

        return redirect(url_for('seller_otp'))

    return render_template('seller_signup.html')


@app.route('/seller_otp', methods=['GET', 'POST'])
def seller_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp', '')

        if entered_otp == str(session.get('otp')):
            name = session.get('name')
            email = session.get('email')
            phone = session.get('phone')
            store_location = session.get('store_location')
            password = session.get('password')

            try:
                insert_seller(name, email, phone, password, store_location)
            except ValueError as e:
                flash(str(e), 'danger')
                return redirect(url_for('seller_signup'))

            # Clear session keys
            for key in ['otp', 'email', 'name', 'phone', 'store_location', 'password']:
                session.pop(key, None)

            flash('Seller signup successful! Please log in.', 'success')
            return redirect(url_for('login'))

        else:
            flash('Invalid OTP. Please try again.', 'danger')

    return render_template('otp.html')

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session or session.get('role') != 'seller':
        flash("Please log in as a seller to access this page.", "warning")
        return redirect(url_for('seller_login'))

    if request.method == 'POST':
        name = request.form['productName']
        image = request.form['productImage']
        category = request.form['productCategory']
        description = request.form['productDescription']
        price = request.form['productPrice']
        quantity = request.form['productQuantity']

        try:
            with closing(get_db()) as conn:
                conn.execute(
    "INSERT INTO products (name, image, category, description, price, quantity, seller_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
    (name, image, category, description, price, quantity, session['user_id'])
)

                conn.commit()

            return redirect(url_for('update_item'))
        except sqlite3.Error as e:
            flash(f"An error occurred: {e}", "danger")
            return redirect(url_for('update_item'))

    return render_template('add_item.html')

@app.route('/update_item')
def update_item():
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('seller_login'))

    with closing(get_db()) as conn:
        products = conn.execute("SELECT * FROM products WHERE seller_id = ?", (session['user_id'],)).fetchall()
    return render_template('update_item.html', products=products)

@app.route('/update_quantity/<int:product_id>/<string:action>', methods=['POST'])
def update_quantity(product_id, action):
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('seller_login'))

    with closing(get_db()) as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ? AND seller_id = ?", (product_id, session['user_id'])).fetchone()

        if not product:
            flash("Product not found or unauthorized", "danger")
            return redirect(url_for('update_item'))

        current_quantity = product['quantity']
        new_quantity = current_quantity + 1 if action == 'increase' else max(0, current_quantity - 1)

        conn.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_quantity, product_id))
        conn.commit()

    return redirect(url_for('update_item'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('seller_login'))

    with closing(get_db()) as conn:
        conn.execute("DELETE FROM products WHERE id = ? AND seller_id = ?", (product_id, session['user_id']))
        conn.commit()

    return redirect(url_for('update_item'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to add items to your cart.", "error")
        return redirect(url_for('login'))

    # Get requested quantity
    try:
        quantity = int(request.form.get('quantity', 1))
        if quantity < 1:
            quantity = 1
    except (ValueError, TypeError):
        quantity = 1

    conn = get_db()
    cur = conn.cursor()

    # Get product quantity (available stock)
    cur.execute("SELECT quantity FROM products WHERE id = ?", (product_id,))
    product = cur.fetchone()
    if not product:
        flash("Product not found.", "error")
        conn.close()
        return redirect(url_for('dashboard'))

    available_quantity = product[0]

    if available_quantity == 0:
        flash("The product is out of stock.", "error")
        conn.close()
        return redirect(url_for('product_view', product_id=product_id))
    elif quantity > available_quantity:
        msg = f"Only {available_quantity} items left in stock."
        flash(msg.strip(), "error")

        conn.close()
        return redirect(url_for('product_view', product_id=product_id))

    # Check if product already in cart
    cur.execute("SELECT quantity FROM cart WHERE user_id=? AND product_id=?", (user_id, product_id))
    item = cur.fetchone()

    if item:
        new_quantity = item[0] + quantity
        # Check if new quantity does not exceed available quantity
        if new_quantity > available_quantity:
            flash(f"Cannot add {quantity} items. You have {item[0]} in your cart and only {available_quantity} in stock.", "error")
            conn.close()
            return redirect(url_for('product_view', product_id=product_id))
        cur.execute("UPDATE cart SET quantity=? WHERE user_id=? AND product_id=?", (new_quantity, user_id, product_id))
    else:
        cur.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, quantity))

    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    conn = get_db()
    cur = conn.cursor()

    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to add items to your cart.", "error")
        return redirect(url_for('login'))
    cur.execute("""
        SELECT products.id, products.name, products.price, products.image, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
    """, (user_id,))
    cart_items = cur.fetchall()

    total = sum(item[2] * item[4] for item in cart_items)  # item[2] is price, item[4] is quantity
    return render_template('addcart.html', cart_items=cart_items, total=total)

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    conn = get_db()
    cur = conn.cursor()

    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view your cart.", "error")
        return redirect(url_for('login'))

    new_quantity = int(request.form['quantity']) 
    # New requested quantity

    # Get the available stock for this product
    cur.execute("SELECT quantity FROM products WHERE id = ?", (product_id,))
    product = cur.fetchone()

    if not product:
        flash("Product not found.", "error")
        conn.close()
        return redirect('/cart')

    available_quantity = product[0]

    if new_quantity > available_quantity:
        flash(f"Only {available_quantity} items left in stock.", "error")
        conn.close()
        return redirect('/cart')

    if new_quantity > 0:
        cur.execute("UPDATE cart SET quantity = ? WHERE user_id=? AND product_id=?", (new_quantity, user_id, product_id))
    else:
        cur.execute("DELETE FROM cart WHERE user_id=? AND product_id=?", (user_id, product_id))

    conn.commit()
    conn.close()
    return redirect('/cart')




@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    conn = get_db()
    cur = conn.cursor()

    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view your cart.", "error")
        return redirect(url_for('login'))
    # Remove the product from the cart
    cur.execute("DELETE FROM cart WHERE user_id=? AND product_id=?", (user_id, product_id))

    conn.commit()
    conn.close()
    return redirect('/cart')

@app.route('/checkout/<int:product_id>', methods=['GET', 'POST'])
def checkout(product_id):
    conn = get_db()
    cur = conn.cursor()

    # Fetch product details including quantity
    cur.execute(""" 
        SELECT id, name, price, image, description, quantity 
        FROM products 
        WHERE id = ? 
    """, (product_id,))
    product = cur.fetchone()

    if not product:
        return "Product not found", 404

    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to complete checkout.", "error")
        return redirect(url_for('login'))

    # ✅ Step 1: Try to get quantity from query parameter
    quantity = request.args.get('quantity', type=int)

    # ✅ Step 2: If not provided in query, fallback to cart
    if quantity is None:
        cur.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        cart_item = cur.fetchone()
        quantity = cart_item['quantity'] if cart_item else 1

# Check if product is out of stock first
    if product['quantity'] == 0:
        flash("Product out of stock.", "error")
        return redirect(url_for('product_view', product_id=product_id))

    # Then check if requested quantity is more than stock
    if quantity > product['quantity']:
        flash(f"Only {product['quantity']} items left in stock.", "error")
        return redirect(url_for('product_view', product_id=product_id))

    total_price = product['price'] * quantity

    # Fetch user's latest address
    cur.execute("""
        SELECT address_line, city, postal_code, state 
        FROM addresses 
        WHERE user_id = ? 
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    address = cur.fetchone()

    if request.method == 'POST':
        address_line = request.form['address']
        city = request.form['city']
        postal_code = request.form['postal_code']
        state = request.form['state']
        payment = request.form.get('payment')

        if not payment:
            flash("Please select a payment method.", "error")
            return redirect(request.url)

        # Save new address if different
        if address is None or address_line != address['address_line']:
            cur.execute("""
                INSERT INTO addresses (user_id, address_line, city, postal_code, state)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, address_line, city, postal_code, state))
            conn.commit()

        full_address = f"{address_line}, {city}, {postal_code}, {state}"
        order_id = random.randint(100000, 999999)

        # ✅ Step 4: Insert order
        cur.execute("""
            INSERT INTO orders (user_id, product_id, quantity, address, payment_method, order_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, product['id'], quantity, full_address, payment, order_id))

        # ✅ Step 5: Update product stock
        cur.execute("""
            UPDATE products
            SET quantity = quantity - ?
            WHERE id = ? AND quantity >= ?
        """, (quantity, product['id'], quantity))

        # ✅ Step 6: Clear from cart
        cur.execute("""
            DELETE FROM cart WHERE user_id = ? AND product_id = ?
        """, (user_id, product_id))

        conn.commit()

        session['order_id'] = order_id
        return redirect(url_for('tracking'))

    return render_template('checkout.html', product=product, quantity=quantity, total_price=total_price, address=address)

@app.route('/tracking')
def tracking():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to track your order.", "error")
        return redirect(url_for('login'))

    order_id = session.get('order_id')  # get order_id from session if present

    conn = get_db()
    cur = conn.cursor()

    if order_id:
        # Fetch the specific order by order_id
        cur.execute("""
            SELECT o.id, o.order_id, o.product_id, o.payment_method, p.name, p.image, o.status, o.quantity,
                   a.address_line, a.city, a.postal_code, a.state
            FROM orders o
            JOIN products p ON o.product_id = p.id
            JOIN addresses a ON o.user_id = a.user_id
            WHERE o.order_id = ?
            LIMIT 1
        """, (order_id,))
    else:
        # Fallback: fetch latest order for user
        cur.execute("""
            SELECT o.id, o.order_id, o.product_id, o.payment_method, p.name, p.image, o.status, o.quantity,
                   a.address_line, a.city, a.postal_code, a.state
            FROM orders o
            JOIN products p ON o.product_id = p.id
            JOIN addresses a ON o.user_id = a.user_id
            WHERE o.user_id = ?
            ORDER BY o.id DESC LIMIT 1
        """, (user_id,))

    order = cur.fetchone()

    if not order:
        flash("No orders found.", "error")
        return redirect(url_for('dashboard'))

    order_id = order[1]
    product = {
        'name': order[4],
        'image': order[5]
    }
    status = order[6]
    quantity = order[7]

    address_line = order[8]
    city = order[9]
    postal_code = order[10]
    state = order[11]
    full_address = f"{address_line}, {city}, {state} - {postal_code}"

    estimated_delivery = (datetime.now() + timedelta(days=5)).strftime("%d-%b-%Y")

    # Clear order_id from session after showing tracking page once
    session.pop('order_id', None)

    return render_template(
        'tracking.html',
        order_id=order_id,
        product=product,
        estimated_delivery=estimated_delivery,
        address=full_address,
        status=status,
        quantity=quantity
    )

@app.route('/track_order')
def track_order():
    order_id = request.args.get('order_id')
    print(f"Tracking order with ID: {order_id}")  # Debugging line
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Fetch the latest status and other details for the order
    c.execute('''SELECT order_id, product_name, product_image, product_price, payment_method, order_date, status, quantity
FROM orders
WHERE order_id = ?
''', (order_id,))
    order = c.fetchone()

    print(f"Order data: {order}")  # Debugging line

    conn.close()

    if order:
        return render_template('track_order.html', order=order)
    else:
        return "Order not found", 404

@app.route('/track')
def track_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''  
        SELECT o.order_id, o.address, o.payment_method, o.order_date, o.status, o.quantity,
       p.name AS product_name, p.price AS product_price, p.image AS product_image
FROM orders o
JOIN products p ON o.product_id = p.id
WHERE o.user_id = ?
ORDER BY o.order_date DESC

    ''', (session['user_id'],))
    orders = c.fetchall()
    conn.close()

    # Now pass the orders directly to the template
    return render_template('track_order.html', orders=orders)

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    data = request.get_json()
    order_id = data.get('order_id')
    status = data.get('status')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    try:
        if status == 'Delivered':
            # Permanently delete the order
            c.execute('DELETE FROM orders WHERE order_id = ?', (order_id,))
        else:
            # Just update the status
            c.execute('UPDATE orders SET status = ? WHERE order_id = ?', (status, order_id))

        conn.commit()
        success = True
    except Exception as e:
        print("Error:", e)
        success = False
    finally:
        conn.close()

    return jsonify({'success': success})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)