import sqlite3
from flask import Flask, request, jsonify, g # Added g
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import os
import jwt # Import PyJWT
import datetime # Import datetime for token expiration
from functools import wraps # Import wraps for decorators
import csv # Import csv module for export
from io import StringIO # Import StringIO for CSV generation
from flask import Response # Import Response for sending CSV file

app = Flask(__name__)

# Get the absolute path of the directory where app.py resides
basedir = os.path.abspath(os.path.dirname(__file__))

# --- Secret Key Configuration ---
# IMPORTANT: Set the FLASK_SECRET_KEY environment variable in your system!
# Use a strong, random key. For development, you can set a default,
# but raise an error if it's not set in a 'production' environment.
# Example command: export FLASK_SECRET_KEY='your-very-strong-random-secret-string'
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default-dev-secret-key-CHANGE-ME!')

# --- CORRECTED CHECK ---
# Check if using the default key when debug mode is OFF (typical for production)
if app.config['SECRET_KEY'] == 'default-dev-secret-key-CHANGE-ME!' and not app.debug:
     # You might want to raise a ValueError or simply log a strong warning here
     # instead of preventing the app from starting entirely during potential staging tests.
     # For now, let's log a warning to the console.
     print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
     print("WARNING: Default SECRET_KEY is used while Flask debug mode is OFF.")
     print("         Set the FLASK_SECRET_KEY environment variable for production.")
     print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
     # If you want to strictly prevent running with the default key in production:
     # raise ValueError("WARNING: Default SECRET_KEY is used in non-debug environment. Set the FLASK_SECRET_KEY environment variable.")

bcrypt = Bcrypt(app)
CORS(app) # Enable CORS for all routes

# Define database paths relative to the backend directory
USER_DATABASE = os.path.join(basedir, 'users.db')
TRADE_DATABASE = os.path.join(basedir, 'trades.db') # New database file for trades
CONTACT_DATABASE = os.path.join(basedir, 'contacts.db') # New database file for contact messages

# --- User Database Helper Functions (Keep Existing) ---
def get_user_db():
    """Connects to the user database using absolute path."""
    db = getattr(g, '_user_database', None)
    if db is None:
        # Connect using the absolute path
        db = g._user_database = sqlite3.connect(USER_DATABASE)
        db.row_factory = sqlite3.Row
    return db

# --- Trade Database Helper Functions (New) ---
def get_trade_db():
    """Connects to the trade database using absolute path."""
    db = getattr(g, '_trade_database', None)
    if db is None:
        # Connect using the absolute path
        db = g._trade_database = sqlite3.connect(TRADE_DATABASE)
        db.row_factory = sqlite3.Row
    return db

# --- Contact Database Helper Functions (New) ---
def get_contact_db():
    """Connects to the contact database using absolute path."""
    db = getattr(g, '_contact_database', None)
    if db is None:
        # Connect using the absolute path
        db = g._contact_database = sqlite3.connect(CONTACT_DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connections(exception):
    """Closes all database connections at the end of the request."""
    user_db = getattr(g, '_user_database', None)
    if user_db is not None:
        user_db.close()
    trade_db = getattr(g, '_trade_database', None)
    if trade_db is not None:
        trade_db.close()
    contact_db = getattr(g, '_contact_database', None)
    if contact_db is not None:
        contact_db.close()

# Modify init_db to handle all databases
def init_db():
    """Initializes the databases and creates tables if they don't exist."""

    # Initialize User Database
    print(f"Checking User Database: {USER_DATABASE}")
    try:
        with app.app_context():
            conn = get_user_db()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
            if not cursor.fetchone():
                print("Creating 'users' table in users.db.")
                cursor.execute("""
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fullname TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        count_completed INTEGER NOT NULL DEFAULT 0, -- Counter for completed trades as seller
                        count_cancelled INTEGER NOT NULL DEFAULT 0, -- Counter for cancelled/declined trades as seller
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                print("'users' table created successfully in users.db.")
            else:
                print("'users' table already exists in users.db.")

            # Check and create cart_items table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cart_items';")
            if not cursor.fetchone():
                print("Creating 'cart_items' table in users.db.")
                cursor.execute("""
                    CREATE TABLE cart_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        trade_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL DEFAULT 1,
                        status TEXT NOT NULL DEFAULT 'pending', -- Status of item in this specific cart (pending, ordered, completed, cancelled)
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        -- Note: No direct FK to trades.db, handled by application logic
                        UNIQUE(user_id, trade_id) -- Prevent duplicate rows for same item/user
                    )
                """)
                conn.commit()
                print("'cart_items' table created successfully in users.db.")
            else:
                print("'cart_items' table already exists in users.db.")
                # Check if 'status' column exists and add if not
                try:
                    cursor.execute("PRAGMA table_info(cart_items)")
                    columns = [column['name'] for column in cursor.fetchall()]
                    if 'status' not in columns:
                        print("Adding 'status' column to existing cart_items table.")
                        # Add with a default value for existing rows
                        cursor.execute("ALTER TABLE cart_items ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
                        conn.commit()
                        print("'status' column added successfully to cart_items.")
                except sqlite3.Error as alter_e:
                    print(f"Could not alter existing cart_items table: {alter_e}")

            # Check and create count_completed and count_cancelled columns
            cursor.execute("PRAGMA table_info(users)")
            columns = [column['name'] for column in cursor.fetchall()]
            if 'count_completed' not in columns:
                print("Adding 'count_completed' column to existing users table.")
                cursor.execute("ALTER TABLE users ADD COLUMN count_completed INTEGER NOT NULL DEFAULT 0")
                conn.commit()
            if 'count_cancelled' not in columns:
                print("Adding 'count_cancelled' column to existing users table.")
                cursor.execute("ALTER TABLE users ADD COLUMN count_cancelled INTEGER NOT NULL DEFAULT 0")
                conn.commit()

    except Exception as e:
        print(f"An error occurred during User DB initialization: {e}")

    # Initialize Trade Database
    print(f"Checking Trade Database: {TRADE_DATABASE}")
    try:
        with app.app_context():
            conn = get_trade_db()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades';")
            if not cursor.fetchone():
                print("Creating 'trades' table in trades.db.")
                cursor.execute("""
                    CREATE TABLE trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        price REAL NOT NULL,
                        quantity INTEGER NOT NULL DEFAULT 1,
                        image TEXT,
                        description TEXT,
                        place TEXT,
                        user_id INTEGER NOT NULL, -- Seller's ID
                        user_fullname TEXT NOT NULL, -- Seller's name
                        rating REAL DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                print("'trades' table created successfully in trades.db.")
            else:
                print("'trades' table already exists in trades.db.")
                # Add alter table logic here if needed for existing DBs
                try:
                    cursor.execute("PRAGMA table_info(trades)")
                    columns = [column['name'] for column in cursor.fetchall()]
                    if 'description' not in columns:
                        print("Adding 'description' column to existing trades table.")
                        cursor.execute("ALTER TABLE trades ADD COLUMN description TEXT")
                        conn.commit()
                    if 'place' not in columns:
                        print("Adding 'place' column to existing trades table.")
                        cursor.execute("ALTER TABLE trades ADD COLUMN place TEXT")
                        conn.commit()
                    if 'user_fullname' not in columns:
                         print("Adding 'user_fullname' column to existing trades table.")
                         cursor.execute("ALTER TABLE trades ADD COLUMN user_fullname TEXT NOT NULL DEFAULT 'Unknown'") # Add default for existing rows
                         conn.commit()
                    if 'rating' not in columns:
                        print("Adding 'rating' column to existing trades table.")
                        cursor.execute("ALTER TABLE trades ADD COLUMN rating REAL DEFAULT NULL")
                        conn.commit()
                    if 'quantity' not in columns:
                        print("Adding 'quantity' column to existing trades table.")
                        cursor.execute("ALTER TABLE trades ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")
                        conn.commit()
                except sqlite3.Error as alter_e:
                    print(f"Could not alter existing trades table: {alter_e}")

            # Check and create ratings table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ratings';")
            if not cursor.fetchone():
                print("Creating 'ratings' table in trades.db.")
                cursor.execute("""
                    CREATE TABLE ratings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trade_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL, -- The ID of the user who submitted the rating
                        rating_score INTEGER NOT NULL CHECK(rating_score >= 1 AND rating_score <= 5), -- Store the actual score (e.g., 1-5)
                        rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (trade_id) REFERENCES trades (id),
                        -- UNIQUE constraint to ensure one rating per user per trade
                        UNIQUE(trade_id, user_id)
                    )
                """)
                conn.commit()
                print("'ratings' table created successfully in trades.db.")
            else:
                print("'ratings' table already exists in trades.db.")

    except Exception as e:
        print(f"An error occurred during Trade DB initialization: {e}")

    # Initialize Contact Database
    print(f"Checking Contact Database: {CONTACT_DATABASE}")
    try:
        with app.app_context():
            conn = get_contact_db()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts';")
            if not cursor.fetchone():
                print("Creating 'contacts' table in contacts.db.")
                cursor.execute("""
                    CREATE TABLE contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        subject TEXT,
                        message TEXT NOT NULL,
                        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                print("'contacts' table created successfully in contacts.db.")
            else:
                print("'contacts' table already exists in contacts.db.")
    except Exception as e:
        print(f"An error occurred during Contact DB initialization: {e}")

# --- JWT Required Decorator (Update to use get_user_db) ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check if jwt is passed in the request header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Expecting "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Bearer token malformed'}), 401

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            # Fetch user from USER database
            conn = get_user_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, fullname, email FROM users WHERE id = ?", (data['user_id'],))
            current_user_row = cursor.fetchone()
            if not current_user_row:
                 return jsonify({'message': 'Token is invalid or user not found!'}), 401
            g.current_user = dict(current_user_row)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
             return jsonify({'message': 'Token is invalid!'}), 401
        except sqlite3.Error as e:
            print(f"Database error during token validation: {e}")
            return jsonify({"message": "Database error during token validation"}), 500
        except Exception as e:
            print(f"Error during token decoding or user fetch: {e}")
            return jsonify({'message': 'Token processing error'}), 500

        return f(*args, **kwargs)
    return decorated

# --- API Routes (Use get_user_db for user operations) ---
@app.route('/api/register', methods=['POST'])
def register():
    """Registers a new user in the SQLite database."""
    data = request.get_json()

    # --- Enhanced Validation ---
    if not data or not data.get('email') or not data.get('password') or not data.get('fullname'):
        return jsonify({"message": "Missing required fields (email, password, fullname)"}), 400

    email = data['email']
    fullname = data['fullname']
    password = data['password']

    # Basic email format check (adjust regex as needed for stricter validation)
    if '@' not in email or '.' not in email.split('@')[-1]:
         return jsonify({"message": "Invalid email format"}), 400

    # Basic password length check
    if len(password) < 6: # Example: require at least 6 characters
        return jsonify({"message": "Password must be at least 6 characters long"}), 400
    # --- End Validation ---


    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = None # Initialize conn to None
    try:
        conn = get_user_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (fullname, email, password, count_completed, count_cancelled) VALUES (?, ?, ?, ?, ?)",
            (fullname, email, hashed_password, 0, 0)
        )
        conn.commit()
        user_id = cursor.lastrowid # Get the ID of the newly inserted user
        print(f"User registered successfully with ID: {user_id}")
        return jsonify({"message": "User registered successfully", "userId": user_id}), 201

    except sqlite3.IntegrityError: # Handles UNIQUE constraint violation for email
        print(f"Registration failed: Email '{email}' already exists.")
        return jsonify({"message": "User already exists with this email"}), 409
    except sqlite3.Error as e:
        print(f"Database error during registration: {e}")
        return jsonify({"message": "Database error during registration"}), 500
    # No finally needed here


@app.route('/api/login', methods=['POST'])
def login():
    """Logs a user in, returns JWT upon success."""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"message": "Missing username or password"}), 400

    # Assuming username field from frontend holds the email
    email = data['username']
    password = data['password']

    conn = None # Initialize conn to None
    try:
        conn = get_user_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user_row = cursor.fetchone() # Fetch one matching user

        if user_row and bcrypt.check_password_hash(user_row['password'], password):
            # User found and password matches
            print(f"Login successful for user: {email} (ID: {user_row['id']})")

            # --- Generate JWT ---
            token = jwt.encode({
                'user_id': user_row['id'],
                'email': user_row['email'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1) # Token expires in 1 hour
            }, app.config['SECRET_KEY'], algorithm="HS256")

            return jsonify({
                "message": "Login successful",
                "token": token, # Send the token to the client
                "user": { # Optionally return some non-sensitive user info
                    "id": user_row['id'],
                    "fullname": user_row['fullname'],
                    "email": user_row['email']
                }
                }), 200
        else:
            # User not found or password incorrect
            print(f"Login failed for email: {email}. User exists: {user_row is not None}")
            return jsonify({"message": "Incorrect email or password"}), 401

    except sqlite3.Error as e:
        print(f"Database error during login: {e}")
        return jsonify({"message": "Database error during login"}), 500
    # No finally needed here


# --- Example Protected Route --- Replaced with Profile Stats
# @app.route('/api/profile', methods=['GET'])
# @token_required
# def get_profile():
#     # ... (previous implementation) ...


# --- Trade API Routes (Use get_trade_db) ---

@app.route('/api/trades', methods=['GET'])
# No @token_required here, but we'll check for token manually
def get_trades():
    """Fetches trade data, optionally checking user's rating status if logged in."""
    conn = get_trade_db()
    cursor = conn.cursor()

    # --- Optional User Authentication ---
    current_user_id = None
    token = None
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        try:
            token = auth_header.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            # Minimal check: Does the user ID exist? (Avoid full DB hit unless needed)
            # We only need the ID here for the query.
            current_user_id = data.get('user_id')
            print(f"Token provided, user ID: {current_user_id}") # Debug log
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, IndexError, KeyError):
            # Ignore invalid/expired tokens for public view, user_id remains None
            print("Invalid/Expired/Malformed token found, proceeding as guest.")
            pass
    # --- End Authentication Check ---

    # Get query parameters
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sortBy', 'name')
    sort_order = request.args.get('sortOrder', 'asc')

    # Validation...
    allowed_sort_columns = ['name', 'price', 'business_name', 'place', 'rating', 'created_at']
    if sort_by not in allowed_sort_columns:
        sort_by = 'name'
    if sort_order.lower() not in ['asc', 'desc']:
        sort_order = 'asc'

    # --- Build the SQL Query ---
    params = []
    # Base selection
    select_clause = """
        SELECT
            t.id,
            t.name,
            t.price,
            t.image,
            t.description,
            t.place,
            t.quantity,
            t.user_id AS seller_id,
            t.user_fullname AS business_name,
            AVG(r.rating_score) as rating, -- Overall average rating for the product
             -- Subquery to get the seller's overall average rating
            (SELECT AVG(sr.rating_score)
             FROM ratings sr
             JOIN trades st ON sr.trade_id = st.id
             WHERE st.user_id = t.user_id) as seller_average_rating
    """

    # Add current user's rating if logged in
    if current_user_id is not None:
        select_clause += ", (SELECT ur.rating_score FROM ratings ur WHERE ur.trade_id = t.id AND ur.user_id = ?) AS current_user_rating_score"
        params.append(current_user_id) # Add user_id to params list FIRST
    else:
        select_clause += ", NULL AS current_user_rating_score" # Return NULL if not logged in

    # FROM and JOIN clauses
    from_join_clause = """
        FROM trades t
        LEFT JOIN ratings r ON t.id = r.trade_id -- For overall average rating
    """

    group_by_clause = " GROUP BY t.id "
    order_by_clause = f" ORDER BY {sort_by} {sort_order.upper()}"

    where_clauses = []
    where_params = [] # Separate params for WHERE clause

    # Add search condition
    if search_query:
        search_term = f'%{search_query}%'
        search_condition = """(
            t.name LIKE ? OR
            t.description LIKE ? OR
            t.place LIKE ? OR
            t.user_fullname LIKE ?
        )"""
        where_clauses.append(search_condition)
        where_params.extend([search_term] * 4)

    # Construct the final SQL
    sql = select_clause + from_join_clause
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += group_by_clause
    sql += order_by_clause

    # Combine params (user ID first if present, then WHERE params)
    final_params = params + where_params

    # --- End Build SQL Query ---

    try:
        print(f"Executing SQL: {sql}")
        print(f"With params: {final_params}")
        cursor.execute(sql, final_params)
        trades = [dict(row) for row in cursor.fetchall()]
        # Convert types
        for trade in trades:
             if trade['price'] is not None: trade['price'] = float(trade['price'])
             if trade['rating'] is not None: trade['rating'] = float(trade['rating'])
             # Add conversion for seller average rating
             if trade['seller_average_rating'] is not None:
                trade['seller_average_rating'] = float(trade['seller_average_rating'])
             # quantity is already an integer from the DB
             # current_user_rating_score will be None or an integer

        return jsonify(trades)
    except sqlite3.Error as e:
        print(f"Database error fetching trades: {e}")
        return jsonify({"message": "Error fetching trade data"}), 500
    except Exception as e:
        print(f"Error fetching trades: {e}")
        return jsonify({"message": "Could not retrieve trade data"}), 500


@app.route('/api/trades', methods=['POST'])
@token_required # Protect this route
def add_trade():
    """Adds a new trade item to trades.db linked to the logged-in user."""
    user_id = g.current_user['id']
    user_fullname = g.current_user['fullname']

    data = request.get_json()

    # Update validation to include new fields
    if not data or not data.get('name') or data.get('price') is None:
        return jsonify({"message": "Missing required fields (name, price)"}), 400

    name = data['name']
    price_str = str(data['price']).strip()
    image = data.get('image', None)
    description = data.get('description', None) # Get description
    place = data.get('place', None)          # Get place
    # Get quantity, default to 1 if not provided or invalid
    try:
        quantity = int(data.get('quantity', 1))
        if quantity < 0: # Allow 0 quantity? For now, let's enforce positive or default to 1
             print("Warning: Received non-positive quantity, defaulting to 1.")
             quantity = 1
    except (ValueError, TypeError):
        print("Warning: Received invalid quantity, defaulting to 1.")
        quantity = 1
    # Rating is not set on creation in this version

    # Validate and convert price
    try:
        price = float(price_str)
        if price < 0:
             return jsonify({"message": "Price cannot be negative"}), 400
    except ValueError:
        return jsonify({"message": "Invalid price format. Please enter a number."}), 400

    conn = get_trade_db() # Use trade DB connection
    cursor = conn.cursor()

    try:
        # Update INSERT statement for new schema (rating defaults to NULL)
        cursor.execute(
            """INSERT INTO trades (name, price, image, description, place, user_id, user_fullname, quantity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, price, image, description, place, user_id, user_fullname, quantity)
        )
        conn.commit()
        trade_id = cursor.lastrowid
        print(f"Trade item '{name}' (ID: {trade_id}) added to trades.db by user {user_fullname} (ID: {user_id}).")

        # Return the added trade details, including new fields
        # Fetch the newly created trade to get default values like rating/created_at
        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        new_trade_row = cursor.fetchone()

        return jsonify({
            "message": "Trade added successfully",
            "tradeId": trade_id,
            "trade": dict(new_trade_row) # Return full new trade details
            }), 201 # 201 Created
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error adding trade: {e}")
        return jsonify({"message": "Database error adding trade"}), 500

# --- Cart API Routes ---

@app.route('/api/cart', methods=['POST'])
@token_required
def add_to_cart():
    """Adds a trade item to the user's cart or updates quantity, checking available stock."""
    user_id = g.current_user['id']
    data = request.get_json()

    if not data or 'trade_id' not in data:
        return jsonify({"message": "Missing 'trade_id' in request body"}), 400

    trade_id = data['trade_id']
    # Default quantity to 1 if not provided or invalid
    try:
        quantity_to_add = int(data.get('quantity', 1))
        if quantity_to_add <= 0:
            # Disallow adding non-positive quantities
            return jsonify({"message": "Quantity to add must be positive"}), 400
    except (ValueError, TypeError):
         return jsonify({"message": "Invalid quantity format"}), 400

    trade_conn = get_trade_db()
    trade_cursor = trade_conn.cursor()
    user_conn = get_user_db() # Cart items are in user DB
    user_cursor = user_conn.cursor()

    try:
        # 1. Check available stock for the trade item
        trade_cursor.execute("SELECT quantity, user_id as seller_id FROM trades WHERE id = ?", (trade_id,))
        trade_info = trade_cursor.fetchone()

        if not trade_info:
             return jsonify({"message": f"Trade item with ID {trade_id} not found"}), 404

        available_stock = trade_info['quantity']
        seller_id = trade_info['seller_id']

        # Prevent seller from adding their own item
        if seller_id == user_id:
            return jsonify({"message": "You cannot add your own listing to the cart"}), 400


        # 2. Check current quantity in cart for this item
        user_cursor.execute(
            "SELECT quantity FROM cart_items WHERE user_id = ? AND trade_id = ?",
            (user_id, trade_id)
        )
        cart_item = user_cursor.fetchone()
        current_cart_qty = cart_item['quantity'] if cart_item else 0

        # 3. Validate requested total quantity against available stock
        potential_new_cart_qty = current_cart_qty + quantity_to_add
        if potential_new_cart_qty > available_stock:
            remaining_can_add = available_stock - current_cart_qty
            return jsonify({
                "message": f"Cannot add {quantity_to_add}. Only {available_stock} available. You already have {current_cart_qty} in cart." +
                           (f" You can add at most {remaining_can_add} more." if remaining_can_add > 0 else "")
            }), 400 # Bad Request - exceeding stock

        # 4. Proceed with insertion/update if validation passes
        # Set status to 'pending' when adding or updating quantity
        user_cursor.execute(
            """INSERT INTO cart_items (user_id, trade_id, quantity, status)
               VALUES (?, ?, ?, 'pending')
               ON CONFLICT(user_id, trade_id) DO UPDATE SET
               quantity = quantity + excluded.quantity,
               status = 'pending'""",
            (user_id, trade_id, quantity_to_add)
        )
        user_conn.commit()

        # Get updated cart item details (optional but good for confirmation)
        # Include status in the fetch confirmation
        user_cursor.execute("SELECT trade_id, quantity, status FROM cart_items WHERE user_id = ? AND trade_id = ?", (user_id, trade_id))
        updated_item = user_cursor.fetchone()
        return jsonify({
            "message": "Item added/updated in cart",
            "item": dict(updated_item) if updated_item else None
            }), 200 # Use 200 OK for add or update

    except sqlite3.Error as e:
        # Rollback both connections if there's an error during the transaction logic
        user_conn.rollback()
        # trade_conn was read-only here, but rollback doesn't hurt
        trade_conn.rollback()
        print(f"Database error adding to cart: {e}")
        return jsonify({"message": "Database error adding to cart"}), 500
    except Exception as e: # Catch potential errors like dict key access
        user_conn.rollback()
        trade_conn.rollback()
        print(f"Unexpected error adding to cart: {e}")
        return jsonify({"message": "An unexpected error occurred while adding to cart"}), 500


@app.route('/api/cart', methods=['GET'])
@token_required
def get_cart():
    """Gets all items in the user's cart with trade details."""
    user_id = g.current_user['id']
    user_conn = get_user_db()
    user_cursor = user_conn.cursor()

    try:
        # Fetch cart item IDs, quantities and status for the user
        user_cursor.execute(
            "SELECT trade_id, quantity, status FROM cart_items WHERE user_id = ?", (user_id,)
        )
        cart_basics = user_cursor.fetchall()

        if not cart_basics:
            return jsonify({"cart": []}), 200 # Return empty cart

        trade_ids = [item['trade_id'] for item in cart_basics]
        # Store quantity and status together, keyed by trade_id
        cart_item_details = {item['trade_id']: {'quantity': item['quantity'], 'status': item['status']} for item in cart_basics}

        # Fetch details for these trades from trades.db
        trade_conn = get_trade_db()
        trade_cursor = trade_conn.cursor()

        # Use placeholders for safe query construction
        placeholders = ','.join('?' * len(trade_ids))
        # Select seller_id (user_id from trades) needed for email lookup
        query = f"""
            SELECT id, name, price, quantity, image, user_id as seller_id, user_fullname as business_name
            FROM trades
            WHERE id IN ({placeholders})
        """
        trade_cursor.execute(query, trade_ids)
        trade_details_list = [dict(row) for row in trade_cursor.fetchall()]

        # --- Fetch Seller Emails ---
        # Prepare seller IDs for querying users.db
        seller_ids = list(set(trade['seller_id'] for trade in trade_details_list)) # Unique seller IDs
        seller_email_map = {}
        if seller_ids:
            user_placeholders = ','.join('?' * len(seller_ids))
            email_query = f"SELECT id, email FROM users WHERE id IN ({user_placeholders})"
            user_cursor.execute(email_query, seller_ids) # Re-use user_cursor from get_user_db()
            seller_emails = user_cursor.fetchall()
            seller_email_map = {row['id']: row['email'] for row in seller_emails}
        # --- End Fetch Seller Emails ---


        # Combine details with quantities, cart status, and emails
        cart_items = []
        for trade in trade_details_list:
            trade_id = trade['id']
            if trade_id in cart_item_details:
                # Add quantity and status from the cart_items table
                trade['quantity'] = cart_item_details[trade_id]['quantity']
                trade['cart_status'] = cart_item_details[trade_id]['status'] # Use 'cart_status' to avoid naming conflict
                # Add seller email from the map
                trade['seller_email'] = seller_email_map.get(trade['seller_id'], None)
                cart_items.append(trade)

        return jsonify({"cart": cart_items}), 200

    except sqlite3.Error as e:
        print(f"Database error fetching cart: {e}")
        return jsonify({"message": "Error fetching cart data"}), 500


@app.route('/api/cart/<int:trade_id>', methods=['DELETE'])
@token_required
def remove_from_cart(trade_id):
    """Removes a specific item from the user's cart."""
    user_id = g.current_user['id']
    conn = get_user_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM cart_items WHERE user_id = ? AND trade_id = ?",
            (user_id, trade_id)
        )
        conn.commit()

        if cursor.rowcount > 0:
            return jsonify({"message": f"Item {trade_id} removed from cart"}), 200
        else:
            return jsonify({"message": f"Item {trade_id} not found in cart"}), 404

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error removing from cart: {e}")
        return jsonify({"message": "Database error removing from cart"}), 500

# --- New endpoint for buyer to mark a cart item as 'ordered' ---
@app.route('/api/cart/items/<int:trade_id>/order', methods=['POST'])
@token_required
def order_cart_item(trade_id):
    """Updates the status of a specific item in the user's cart to 'ordered'."""
    user_id = g.current_user['id']
    conn = get_user_db()
    cursor = conn.cursor()

    try:
        # Check if the item exists in the cart and is in 'pending' status
        cursor.execute(
            "SELECT id, status FROM cart_items WHERE user_id = ? AND trade_id = ?",
            (user_id, trade_id)
        )
        cart_item = cursor.fetchone()

        if not cart_item:
            return jsonify({"message": f"Item {trade_id} not found in your cart."}), 404

        if cart_item['status'] != 'pending':
            return jsonify({"message": f"Item cannot be ordered from its current status ('{cart_item['status']}')"}), 400

        # Update the status to 'ordered'
        cursor.execute(
            "UPDATE cart_items SET status = 'ordered' WHERE id = ?",
            (cart_item['id'],) # Use the cart_item PK for precision
        )
        conn.commit()

        if cursor.rowcount == 0:
            # Should not happen if first checks passed, but for safety
            return jsonify({"message": "Failed to update cart item status."}), 500

        print(f"Cart item (trade_id: {trade_id}) marked as ordered by user {user_id}.")
        return jsonify({"message": "Item successfully marked as ordered in cart", "new_status": "ordered"}), 200

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error ordering cart item {trade_id}: {e}")
        return jsonify({"message": "Database error processing order request"}), 500
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error ordering cart item {trade_id}: {e}")
        return jsonify({"message": "An unexpected error occurred while processing the order"}), 500

# --- Profile Stats Route (Updated) ---

@app.route('/api/profile/stats', methods=['GET'])
@token_required
def get_profile_stats():
    """Gets user's listed items and overall seller rating."""
    user_id = g.current_user['id']
    conn = get_trade_db()
    cursor = conn.cursor()

    seller_avg_rating = None
    listings = []

    try:
        # 1. Fetch all trades listed by the user (for display on profile)
        cursor.execute(
            """SELECT t.id, t.name, t.price, t.quantity, t.image, t.description, t.place, t.created_at,
                      AVG(r.rating_score) as average_product_rating -- Also fetch avg rating per product
               FROM trades t
               LEFT JOIN ratings r ON t.id = r.trade_id
               WHERE t.user_id = ?
               GROUP BY t.id -- Group by trade to get avg rating per trade
               ORDER BY t.created_at DESC""",
            (user_id,)
        )
        listings_raw = cursor.fetchall()
        listings = []
        for row in listings_raw:
            item = dict(row)
            # Ensure numeric types are correct for listings
            if item.get('price') is not None: item['price'] = float(item['price'])
            if item.get('quantity') is not None: item['quantity'] = int(item['quantity'])
            if item.get('average_product_rating') is not None: item['average_product_rating'] = float(item['average_product_rating'])
            listings.append(item)

        # 2. Calculate the overall average rating for the SELLER (from trades.db)
        # This part remains the same, based on the ratings table
        cursor.execute(
            """SELECT AVG(r.rating_score)
               FROM ratings r
               JOIN trades t ON r.trade_id = t.id
               WHERE t.user_id = ?""",
            (user_id,)
        )
        avg_result = cursor.fetchone()
        if avg_result and avg_result[0] is not None:
            seller_avg_rating = round(float(avg_result[0]), 2)

        # 3. Fetch completion/cancellation counts from users.db
        user_conn = get_user_db() # Need user DB connection
        user_cursor = user_conn.cursor()
        user_cursor.execute(
            "SELECT count_completed, count_cancelled FROM users WHERE id = ?",
            (user_id,)
        )
        user_counts = user_cursor.fetchone()

        count_completed = 0
        count_cancelled = 0
        if user_counts:
            count_completed = user_counts['count_completed']
            count_cancelled = user_counts['count_cancelled']

        # 4. Calculate successful trade percentage using the counters
        successful_trade_percentage = 0
        total_finalized = count_completed + count_cancelled
        if total_finalized > 0:
             successful_trade_percentage = round((count_completed / total_finalized) * 100, 1)

        return jsonify({
            "listings": listings,
            "seller_average_rating": seller_avg_rating,
            "successful_trades_percentage": successful_trade_percentage
            }), 200

    except sqlite3.Error as e:
        print(f"Database error fetching profile stats: {e}")
        return jsonify({"message": "Error fetching profile statistics"}), 500

# --- Export Route (New) ---
@app.route('/api/trades/export', methods=['GET'])
# Optional: Protect with @token_required if only logged-in users should export
def export_trades_csv():
    """Exports all trade data to a CSV file."""
    try:
        conn = get_trade_db()
        cursor = conn.cursor()
        # Include rating in export - REMOVED 'rating' as it's not a direct column
        cursor.execute("SELECT id, name, price, description, place, user_id, user_fullname, created_at FROM trades ORDER BY created_at DESC")
        trades = cursor.fetchall()

        # Use StringIO to create CSV in memory
        si = StringIO()
        cw = csv.writer(si)

        # Write Header
        column_names = [description[0] for description in cursor.description]
        cw.writerow(column_names)

        # Write Data Rows
        cw.writerows(trades)

        # Prepare response
        output = si.getvalue()
        si.close()

        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-disposition":
                     "attachment; filename=trades_export.csv"}
        )

    except sqlite3.Error as e:
        print(f"Database error during CSV export: {e}")
        return jsonify({"message": "Error exporting trade data"}), 500
    except Exception as e:
        print(f"General error during CSV export: {e}")
        return jsonify({"message": "Could not generate trade export"}), 500

# --- New Trade Action Endpoints ---

@app.route('/api/trades/<int:trade_id>/rate', methods=['POST'])
@token_required
def rate_trade(trade_id):
    data = request.get_json()
    # Expect 'rating_score' instead of 'rating'
    if not data or 'rating_score' not in data:
        return jsonify({"message": "Rating score is required"}), 400

    try:
        # Validate rating score (must be integer 1-5)
        rating_score = int(data['rating_score'])
        if not (1 <= rating_score <= 5):
             raise ValueError("Rating score must be between 1 and 5")
    except (ValueError, TypeError):
         return jsonify({"message": "Invalid rating score (must be an integer between 1 and 5)"}), 400

    user_id = g.current_user['id'] # User performing the rating

    trade_conn = get_trade_db()
    trade_cursor = trade_conn.cursor()
    user_conn = get_user_db()
    user_cursor = user_conn.cursor()

    try:
        # --- Rating Restrictions ---
        # 1. Get seller ID from trade (trades.db)
        trade_cursor.execute("SELECT user_id FROM trades WHERE id = ?", (trade_id,))
        trade = trade_cursor.fetchone()
        if not trade:
            return jsonify({"message": "Trade not found"}), 404
        seller_id = trade['user_id']

        # 2. Check if the rater is the seller (same as before)
        if seller_id == user_id:
            return jsonify({"message": "Sellers cannot rate their own trades"}), 403 # Forbidden

        # 3. Check if the rater has a completed cart item for this trade (users.db)
        user_cursor.execute(
            "SELECT status FROM cart_items WHERE user_id = ? AND trade_id = ?",
            (user_id, trade_id)
        )
        cart_item = user_cursor.fetchone()

        if not cart_item:
            return jsonify({"message": "You have not purchased this item."}), 400 # Or 404/403?
        if cart_item['status'] != 'completed':
            return jsonify({"message": f"You can only rate items marked as completed in your order history (current status: '{cart_item['status']}')"}), 400
        # --- End Rating Restrictions ---

        # --- Insert or Replace the rating in the 'ratings' table (trades.db) ---
        # Note: Using trade_cursor here as ratings table is in trades.db
        trade_cursor.execute("""
            INSERT INTO ratings (trade_id, user_id, rating_score)
            VALUES (?, ?, ?)
            ON CONFLICT(trade_id, user_id) DO UPDATE SET
                rating_score = excluded.rating_score,
                rated_at = CURRENT_TIMESTAMP
        """, (trade_id, user_id, rating_score))
        # --- End Insert/Replace ---

        trade_conn.commit() # Commit on the connection where the insert happened (trades_db)
        # Use 200 OK for simplicity, indicates the action was successful (create or update)
        return jsonify({"message": "Rating submitted successfully"}), 200

    except sqlite3.IntegrityError as e: # Should be caught by ON CONFLICT, but good practice
        trade_conn.rollback() # Rollback on the connection where the insert happened
        # This specific error is less likely now with ON CONFLICT, but might catch other issues
        print(f"Integrity error rating trade: {e}")
        return jsonify({"message": f"Could not submit rating due to a data conflict: {e}"}), 409 # Conflict
    except sqlite3.Error as e:
        trade_conn.rollback()
        print(f"Database error rating trade: {e}")
        return jsonify({"message": "Database error processing rating"}), 500
    except Exception as e:
        trade_conn.rollback()
        print(f"Error rating trade: {e}")
        return jsonify({"message": "Error processing rating"}), 500


@app.route('/api/trades/<int:trade_id>/complete', methods=['POST'])
@token_required
def complete_trade(trade_id):
    # Check if the logged-in user is the SELLER of the trade
    user_id = g.current_user['id']
    conn = get_trade_db()
    cursor = conn.cursor()

    try:
        # Verify ownership and status before completing
        cursor.execute("SELECT user_id FROM trades WHERE id = ?", (trade_id,)) # Removed status check
        trade = cursor.fetchone()

        if not trade:
            return jsonify({"message": "Trade item not found"}), 404

        if trade['user_id'] != user_id:
            return jsonify({"message": "You are not authorized to complete this trade"}), 403 # Forbidden


        # --- THIS ENDPOINT LOGIC IS INVALID and DEPRECATED ---
        # It needs to be replaced by seller accepting an order from a specific buyer via cart_items

        return jsonify({"message": "This endpoint is deprecated. Use seller order management."}), 410 # Gone

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error completing trade: {e}")
        return jsonify({"message": "Database error completing trade"}), 500

# --- New endpoint to delete a trade ---
@app.route('/api/trades/<int:trade_id>', methods=['DELETE'])
@token_required
def delete_trade(trade_id):
    """Deletes a trade item if the logged-in user is the seller."""
    user_id = g.current_user['id']
    trade_conn = get_trade_db()
    trade_cursor = trade_conn.cursor()
    user_conn = get_user_db() # Get connection to users DB for cart cleanup
    user_cursor = user_conn.cursor()

    try:
        # 1. Verify the trade exists and the current user is the seller (from trades.db)
        trade_cursor.execute("SELECT user_id FROM trades WHERE id = ?", (trade_id,))
        trade = trade_cursor.fetchone()

        if not trade:
            return jsonify({"message": "Trade not found"}), 404

        if trade['user_id'] != user_id:
            return jsonify({"message": "You are not authorized to delete this trade"}), 403 # Forbidden

        # --- Database Operations ---
        # Wrap in separate try/commit blocks as cross-db transactions are complex

        # 2. Attempt to delete associated cart items (from users.db)
        deleted_cart_count = 0
        try:
            user_cursor.execute("DELETE FROM cart_items WHERE trade_id = ?", (trade_id,))
            user_conn.commit() # Commit cart item deletion
            deleted_cart_count = user_cursor.rowcount
            print(f"Deleted {deleted_cart_count} associated cart items for trade {trade_id}.")
        except sqlite3.Error as user_e:
            user_conn.rollback()
            # Log the error but proceed with trade deletion as ownership is confirmed
            print(f"WARNING: Database error deleting associated cart items for trade {trade_id}: {user_e}. Proceeding with trade deletion.")

        # 3. Delete the trade itself (from trades.db)
        try:
            trade_cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
            trade_conn.commit() # Commit trade deletion
            deleted_trade_count = trade_cursor.rowcount

            if deleted_trade_count == 0:
                # This shouldn't happen if initial check passed, but indicates an issue.
                print(f"ERROR: Trade {trade_id} not found during deletion attempt after initial check.")
                # Since cart items might have been deleted, report an error.
                return jsonify({"message": "Trade deletion failed unexpectedly after initial check."}), 500

            print(f"Trade {trade_id} deleted successfully by user {user_id}.")
            return jsonify({"message": "Trade deleted successfully", "deleted_cart_items": deleted_cart_count}), 200

        except sqlite3.Error as trade_e:
            trade_conn.rollback()
            print(f"Database error deleting trade {trade_id} itself: {trade_e}")
            # Report error, as the primary resource deletion failed.
            return jsonify({"message": "Database error deleting trade"}), 500

    except sqlite3.Error as db_e:
        # Error during initial trade fetch/verification
        print(f"Database error verifying trade {trade_id} for deletion: {db_e}")
        return jsonify({"message": "Database error checking trade before deletion"}), 500
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected error deleting trade {trade_id}: {e}")
        return jsonify({"message": "An unexpected error occurred while deleting the trade"}), 500

# --- New endpoint to get incoming orders for the logged-in seller ---
@app.route('/api/profile/incoming_orders', methods=['GET'])
@token_required
def get_incoming_orders():
    """Gets items listed by the seller that buyers have marked as 'ordered' in their carts."""
    seller_id = g.current_user['id']
    # Main connection will be to users.db, we'll attach trades.db
    user_conn = get_user_db()
    cursor = user_conn.cursor()

    # Get the absolute path for trades.db to ensure attach works reliably
    trades_db_path = TRADE_DATABASE

    try:
        # Attach the trades database to the current user database connection
        cursor.execute(f"ATTACH DATABASE ? AS trades_db", (trades_db_path,))
        print(f"Attached trades DB: {trades_db_path}") # Debug log

        # Query across both databases
        query = """
            SELECT
                ci.id AS cart_item_id,
                ci.quantity AS ordered_quantity,
                ci.added_at AS ordered_at,
                t.id AS trade_id,
                t.name AS trade_name,
                t.price AS trade_price,
                t.image AS trade_image,
                t.description AS trade_description,
                t.place AS trade_place,
                b.id AS buyer_id,
                b.fullname AS buyer_fullname,
                b.email AS buyer_email
            FROM
                cart_items ci
            JOIN
                users b ON ci.user_id = b.id -- Join buyer details from users table
            JOIN
                trades_db.trades t ON ci.trade_id = t.id -- Join trade details from attached trades table
            WHERE
                t.user_id = ? -- Filter: Trade belongs to the logged-in seller
                AND ci.status = 'ordered' -- Filter: Cart item status is 'ordered'
            ORDER BY
                ci.added_at DESC; -- Show newest orders first
        """
        cursor.execute(query, (seller_id,))
        incoming_orders_raw = cursor.fetchall()
        incoming_orders = [dict(row) for row in incoming_orders_raw]

        # Ensure numeric types are correct (price)
        for item in incoming_orders:
            if item.get('trade_price') is not None: item['trade_price'] = float(item['trade_price'])
            # quantity is integer

        # Detach the database
        cursor.execute("DETACH DATABASE trades_db")
        print("Detached trades DB") # Debug log

        return jsonify({"incoming_orders": incoming_orders}), 200

    except sqlite3.Error as e:
        # Ensure detachment even on error if possible
        try:
             cursor.execute("DETACH DATABASE trades_db")
        except sqlite3.Error:
             pass # Ignore error during detach if it wasn't attached or already detached
        print(f"Database error fetching incoming orders: {e}")
        return jsonify({"message": "Error fetching incoming orders"}), 500
    except Exception as e:
         # Ensure detachment even on error if possible
        try:
             cursor.execute("DETACH DATABASE trades_db")
        except sqlite3.Error:
             pass
        print(f"Unexpected error fetching incoming orders: {e}")
        return jsonify({"message": "An unexpected error occurred while fetching incoming orders"}), 500

# --- New endpoints for seller to accept/decline orders ---

@app.route('/api/seller/orders/accept', methods=['POST'])
@token_required
def seller_accept_order():
    """Allows seller to accept an 'ordered' cart item.
       Updates cart status, increments seller's completed count, and decrements trade stock.
    """
    seller_id = g.current_user['id']
    data = request.get_json()

    if not data or 'cart_item_id' not in data:
        return jsonify({"message": "Missing 'cart_item_id' in request body"}), 400

    cart_item_id = data['cart_item_id']

    user_conn = get_user_db()
    user_cursor = user_conn.cursor()
    trade_conn = get_trade_db()
    trade_cursor = trade_conn.cursor()

    try:
        # 1. Fetch cart item and buyer ID (from users.db)
        user_cursor.execute(
            "SELECT user_id, trade_id, quantity, status FROM cart_items WHERE id = ?",
            (cart_item_id,)
        )
        cart_item = user_cursor.fetchone()

        if not cart_item:
            return jsonify({"message": "Cart item not found"}), 404
        if cart_item['status'] != 'ordered':
            return jsonify({"message": f"Cart item is not in 'ordered' status (current: {cart_item['status']})"}), 400

        trade_id = cart_item['trade_id']
        ordered_quantity = cart_item['quantity']
        buyer_id = cart_item['user_id'] # Keep buyer_id for potential future use

        # 2. Fetch trade details and verify seller ownership and stock (from trades.db)
        trade_cursor.execute(
            "SELECT user_id, quantity FROM trades WHERE id = ?",
            (trade_id,)
        )
        trade = trade_cursor.fetchone()

        if not trade:
             # If trade was deleted after order, cart item should perhaps be cancelled?
             # For now, return error indicating trade not found.
            return jsonify({"message": "Associated trade not found"}), 404
        if trade['user_id'] != seller_id:
            return jsonify({"message": "You are not authorized to manage this trade item"}), 403
        if trade['quantity'] < ordered_quantity:
            # Not enough stock - maybe cancel the order automatically?
            # For now, return error to seller. They might need to manually cancel.
            return jsonify({
                "message": f"Insufficient stock ({trade['quantity']}) to fulfill ordered quantity ({ordered_quantity}). Decline the order."
            }), 400

        # --- Perform Updates (Prioritize user DB updates) ---

        # 3. Update user DB within a transaction
        try:
            user_conn.execute("BEGIN") # Start transaction on user_conn explicitly

            # Update cart item status to 'completed'
            user_cursor.execute(
                "UPDATE cart_items SET status = 'completed' WHERE id = ?",
                (cart_item_id,)
            )
            if user_cursor.rowcount == 0:
                 raise sqlite3.Error("Failed to update cart item status (rowcount 0).") # Force rollback

            # Increment seller's completed count
            user_cursor.execute(
                "UPDATE users SET count_completed = count_completed + 1 WHERE id = ?",
                (seller_id,)
            )
            if user_cursor.rowcount == 0:
                 raise sqlite3.Error("Failed to update seller completion count (rowcount 0).") # Force rollback

            user_conn.commit() # Commit user DB changes
            print(f"User DB commit successful for accepting cart_item {cart_item_id}")

        except sqlite3.Error as user_e:
            user_conn.rollback() # Rollback user DB changes on error
            print(f"User DB transaction failed for accepting cart_item {cart_item_id}: {user_e}")
            return jsonify({"message": "Database error during order acceptance (user data)"}), 500

        # 4. Decrement stock in trade DB (Separate commit - potential inconsistency)
        try:
            trade_cursor.execute(
                "UPDATE trades SET quantity = quantity - ? WHERE id = ?",
                (ordered_quantity, trade_id)
            )
            trade_conn.commit() # Commit trade DB change
            if trade_cursor.rowcount == 0:
                # This is bad: user updates committed, but stock failed. Log it.
                print(f"CRITICAL ERROR: Failed to decrement stock for trade {trade_id} after cart_item {cart_item_id} was accepted.")
                # Return success to user, but log the inconsistency.
            else:
                 print(f"Trade DB stock successfully decremented for trade {trade_id}")

        except sqlite3.Error as trade_e:
            trade_conn.rollback()
            # Log critical error: User changes committed, stock decrement failed.
            print(f"CRITICAL ERROR: Database error decrementing stock for trade {trade_id} after cart_item {cart_item_id} acceptance: {trade_e}")
            # Return success to the user for the primary action, but log inconsistency.

        print(f"Order accepted for cart_item {cart_item_id} by seller {seller_id}.")
        return jsonify({"message": "Order accepted successfully"}), 200

    except sqlite3.Error as db_e:
        # Catch errors during initial fetches before transactions
        print(f"Database error during initial fetch for accepting order: {db_e}")
        return jsonify({"message": "Database error processing acceptance request"}), 500
    except Exception as e:
        print(f"Unexpected error accepting order: {e}")
        return jsonify({"message": "An unexpected error occurred"}), 500

@app.route('/api/seller/orders/decline', methods=['POST'])
@token_required
def seller_decline_order():
    """Allows seller to decline an 'ordered' cart item.
       Updates cart status to 'cancelled' and increments seller's cancelled count.
    """
    seller_id = g.current_user['id']
    data = request.get_json()

    if not data or 'cart_item_id' not in data:
        return jsonify({"message": "Missing 'cart_item_id' in request body"}), 400

    cart_item_id = data['cart_item_id']

    user_conn = get_user_db()
    user_cursor = user_conn.cursor()
    trade_conn = get_trade_db() # Still needed to check trade ownership
    trade_cursor = trade_conn.cursor()

    try:
        # 1. Fetch cart item and buyer ID (from users.db)
        user_cursor.execute(
            "SELECT user_id, trade_id, status FROM cart_items WHERE id = ?",
            (cart_item_id,)
        )
        cart_item = user_cursor.fetchone()

        if not cart_item:
            return jsonify({"message": "Cart item not found"}), 404
        if cart_item['status'] != 'ordered':
            return jsonify({"message": f"Cart item is not in 'ordered' status (current: {cart_item['status']})"}), 400

        trade_id = cart_item['trade_id']

        # 2. Verify seller ownership (from trades.db)
        trade_cursor.execute(
            "SELECT user_id FROM trades WHERE id = ?",
            (trade_id,)
        )
        trade = trade_cursor.fetchone()
        if not trade:
            return jsonify({"message": "Associated trade not found"}), 404
        if trade['user_id'] != seller_id:
            return jsonify({"message": "You are not authorized to manage this trade item"}), 403

        # 3. Update user DB within a transaction
        try:
            user_conn.execute("BEGIN") # Start transaction

            # Update cart item status to 'cancelled'
            user_cursor.execute(
                "UPDATE cart_items SET status = 'cancelled' WHERE id = ?",
                (cart_item_id,)
            )
            if user_cursor.rowcount == 0:
                 raise sqlite3.Error("Failed to update cart item status (rowcount 0).") # Force rollback

            # Increment seller's cancelled count
            user_cursor.execute(
                "UPDATE users SET count_cancelled = count_cancelled + 1 WHERE id = ?",
                (seller_id,)
            )
            if user_cursor.rowcount == 0:
                 raise sqlite3.Error("Failed to update seller cancellation count (rowcount 0).") # Force rollback

            user_conn.commit() # Commit user DB changes
            print(f"Order declined (cart_item {cart_item_id}) by seller {seller_id}. User DB commit successful.")
            return jsonify({"message": "Order declined successfully"}), 200

        except sqlite3.Error as user_e:
            user_conn.rollback() # Rollback user DB changes on error
            print(f"User DB transaction failed for declining cart_item {cart_item_id}: {user_e}")
            return jsonify({"message": "Database error during order decline (user data)"}), 500

    except sqlite3.Error as db_e:
        # Catch errors during initial fetches before transactions
        print(f"Database error during initial fetch for declining order: {db_e}")
        return jsonify({"message": "Database error processing decline request"}), 500
    except Exception as e:
        print(f"Unexpected error declining order: {e}")
        return jsonify({"message": "An unexpected error occurred"}), 500

# --- Function to export contacts to CSV (New) ---
def export_contacts_to_csv():
    """Fetches all contacts from contacts.db and writes them to a CSV file in the backend folder."""
    csv_filename = os.path.join(basedir, 'contacts_export.csv')
    print(f"Attempting to export contacts to: {csv_filename}")

    conn = None # Initialize conn
    try:
        conn = get_contact_db() # Use the helper function
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, subject, message, submitted_at FROM contacts ORDER BY submitted_at DESC")
        contacts = cursor.fetchall()

        # Write to CSV
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # Write Header from cursor description
            column_names = [description[0] for description in cursor.description]
            csv_writer.writerow(column_names)
            
            # Write Data Rows
            csv_writer.writerows(contacts)
            
        print(f"Successfully exported {len(contacts)} contacts to {csv_filename}")

    except sqlite3.Error as e:
        print(f"Database error during contact CSV export: {e}")
        # Decide if you want to raise the error or just log it
        # raise e # Optionally re-raise if the calling function should handle it
    except IOError as e:
        print(f"File I/O error during contact CSV export: {e}")
    except Exception as e:
        print(f"General error during contact CSV export: {e}")
    # No finally block needed as we are not closing the connection here (app context teardown handles it)


# --- Contact Form Submission Route (Modified) ---
@app.route('/api/contact', methods=['POST'])
def handle_contact_form():
    """Handles submission from the contact form and triggers CSV export."""
    data = request.get_json()

    if not data or not data.get('name') or not data.get('email') or not data.get('message'):
        return jsonify({"message": "Missing required fields (name, email, message)"}), 400

    name = data['name']
    email = data['email']
    subject = data.get('subject', '') # Subject is optional
    message = data['message']

    # Basic email format check
    if '@' not in email or '.' not in email.split('@')[-1]:
         return jsonify({"message": "Invalid email format"}), 400

    conn = None
    try:
        conn = get_contact_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)",
            (name, email, subject, message)
        )
        conn.commit()
        contact_id = cursor.lastrowid
        print(f"Contact message received successfully with ID: {contact_id}")

        # --- Trigger CSV Export --- 
        export_contacts_to_csv() # Call the export function after successful insert
        # --- End Trigger --- 

        return jsonify({"message": "Contact message received successfully", "contactId": contact_id}), 201 # 201 Created

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error saving contact message: {e}")
        return jsonify({"message": "Database error saving message"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Unexpected error saving contact message: {e}")
        return jsonify({"message": "An unexpected error occurred saving the message"}), 500


# --- Main execution block ---
if __name__ == '__main__':
    init_db() # Initialize DBs on startup
    print(f"SECRET_KEY in use: {app.config['SECRET_KEY'][:5]}... (Check console warning if this is the default key!)")
    app.run(debug=True, port=5000) 
