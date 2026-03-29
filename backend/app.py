import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify, g
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import os
import jwt
import datetime
from functools import wraps
import csv
from io import StringIO
from flask import Response
from dotenv import load_dotenv
import urllib.parse

# --- VietQR Bank ID Mapping --- 
VIETQR_BANK_MAP = {
    "VietinBank": "970415",
    "Vietcombank": "970436",
    "BIDV": "970418",
    "Agribank": "970405",
    "OCB": "970448",
    "MBBank": "970422",
    "Techcombank": "970407",
    "ACB": "970416",
    "VPBank": "970432",
    "TPBank": "970423",
    "Sacombank": "970403",
    "HDBank": "970437",
    "VietCapitalBank": "970454",
    "SCB": "970429",
    "VIB": "970441",
    "SHB": "970443",
    "Eximbank": "970431",
    "MSB": "970426",
    "CAKE": "546034",
    "Ubank": "546035",
    "Timo": "963388",
    "ViettelMoney": "971005",
    "VNPTMoney": "971011",
    "SaigonBank": "970400",
    "BacABank": "970409",
    "PVcomBank": "970412",
    "Oceanbank": "970414",
    "NCB": "970419",
    "ShinhanBank": "970424",
    "ABBANK": "970425",
    "VietABank": "970427",
    "NamABank": "970428",
    "PGBank": "970430",
    "VietBank": "970433",
    "BaoVietBank": "970438",
    "SeABank": "970440",
    "COOPBANK": "970446",
    "LPBank": "970449",
    "KienLongBank": "970452",
    "KBank": "668888",
    "KookminHN": "970462",
    "KEBHanaHCM": "970466",
    "KEBHanaHN": "970467",
    "MAFC": "977777",
    "Citibank": "533948",
    "KookminHCM": "970463",
    "VBSP": "999888",
    "Woori": "970457",
    "VRB": "970421",
    "UnitedOverseas": "970458",
    "StandardChartered": "970410",
    "PublicBank": "970439",
    "Nonghyup": "801011",
    "IndovinaBank": "970434",
    "IBKHCM": "970456",
    "IBKHN": "970455",
    "HSBC": "458761",
    "HongLeong": "970442",
    "GPBank": "970408",
    "DongABank": "970406",
    "DBSBank": "796500",
    "CIMB": "422589",
    "CBBank": "970444",
}

# Load environment variables from .env in the current or parent directory
load_dotenv()

app = Flask(__name__)

# --- Get DATABASE_URL from environment ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("No DATABASE_URL set for Flask application")


# Get the absolute path of the directory where app.py resides
basedir = os.path.abspath(os.path.dirname(__file__))

# --- Secret Key Configuration ---
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default-dev-secret-key-CHANGE-ME!')

# --- CORRECTED CHECK ---
if app.config['SECRET_KEY'] == 'default-dev-secret-key-CHANGE-ME!' and not app.debug:
     print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
     print("WARNING: Default SECRET_KEY is used while Flask debug mode is OFF.")
     print("         Set the FLASK_SECRET_KEY environment variable for production.")
     print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

bcrypt = Bcrypt(app)
CORS(app) # Enable CORS for all routes


# --- PostgreSQL Database Helper Functions ---
def get_db():
    """Connects to the PostgreSQL database using the DATABASE_URL.
       Connection is stored in Flask's g context for reuse during a request.
    """
    if 'db' not in g:
        try:
            print(f"Attempting to connect to database...")
            g.db = psycopg2.connect(DATABASE_URL)
            print(f"Database connection successful.")
        except psycopg2.OperationalError as e:
            print(f"!!! DATABASE CONNECTION FAILED: {e}")
            raise e
    return g.db

@app.teardown_appcontext
def close_connections(exception):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
        print("Database connection closed.")


def init_db():
    """Initializes the PostgreSQL database and creates tables if they don't exist."""
    print("Attempting to initialize database tables...")
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Drop tables in reverse order of creation
        print("Dropping existing tables (if they exist)...")
        cursor.execute("DROP TABLE IF EXISTS contacts CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS ratings CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS cart_items CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS trades CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS users CASCADE;")
        # --- Users Table ---
        print("Creating 'users' table...")
        cursor.execute("""
            CREATE TABLE users ( -- Removed IF NOT EXISTS
                id SERIAL PRIMARY KEY,
                fullname VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password TEXT NOT NULL, -- Storing hashed password
                count_completed INTEGER NOT NULL DEFAULT 0,
                count_cancelled INTEGER NOT NULL DEFAULT 0,
                bank_name TEXT NULL,
                bank_account_number TEXT NULL,
                bank_account_name TEXT NULL,
                status VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # --- Trades Table ---
        print("Creating 'trades' table...")
        cursor.execute("""
            CREATE TABLE trades ( -- Removed IF NOT EXISTS
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity >= 0),
                image TEXT,
                description TEXT,
                place TEXT,
                user_id INTEGER NOT NULL, -- Seller's ID
                user_fullname VARCHAR(255) NOT NULL, -- Seller's name (denormalized)
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        # --- Cart Items Table ---
        print("Creating 'cart_items' table...")
        cursor.execute("""
            CREATE TABLE cart_items ( -- Removed IF NOT EXISTS
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                trade_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity > 0),
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                added_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (trade_id) REFERENCES trades (id) ON DELETE CASCADE
            );
        """)

        # --- Ratings Table ---
        print("Creating 'ratings' table...")
        cursor.execute("""
            CREATE TABLE ratings ( -- Removed IF NOT EXISTS
                id SERIAL PRIMARY KEY,
                trade_id INTEGER NULL, -- Allow NULL
                user_id INTEGER NOT NULL, -- Buyer/Rater ID
                seller_id INTEGER NULL, --  Seller ID
                cart_item_id INTEGER NULL, -- Allow NULL
                rating_score INTEGER NOT NULL CHECK(rating_score >= 1 AND rating_score <= 5),
                rated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES trades (id) ON DELETE SET NULL, -- Keep rating if trade deleted
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL, -- Keep rating if rater deleted
                FOREIGN KEY (seller_id) REFERENCES users (id) ON DELETE CASCADE, -- Delete rating if seller deleted
                FOREIGN KEY (cart_item_id) REFERENCES cart_items (id) ON DELETE SET NULL, -- Keep rating if cart item deleted
                UNIQUE(cart_item_id) -- Ensure only one rating per non-null cart item
            );
        """)

        # --- Contacts Table ---
        print("Creating 'contacts' table...")
        cursor.execute("""
            CREATE TABLE contacts ( -- Removed IF NOT EXISTS
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                submitted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cursor.close()
        print("Database table initialization complete.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error during database initialization: {error}")
        if conn:
            conn.rollback() # Roll back changes if any error occurred
    finally:
        pass


# --- JWT Required Decorator (Update to use get_db) ---
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
            # Fetch user from the database using PostgreSQL connection
            conn = get_db()
            # Use DictCursor to access columns by name
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            # Use %s placeholder for PostgreSQL
            # Fetch payment info along with basic user details
            cursor.execute(
                "SELECT id, fullname, email, bank_name, bank_account_number, bank_account_name "
                "FROM users WHERE id = %s", 
                (data['user_id'],)
            )
            current_user_row = cursor.fetchone()
            cursor.close() # Close cursor after use
            if not current_user_row:
                 return jsonify({'message': 'Token is invalid or user not found!'}), 401
            # g.current_user can be the DictRow object itself or convert to dict
            g.current_user = current_user_row # Store the fetched user row in g
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
             return jsonify({'message': 'Token is invalid!'}), 401
        # Catch PostgreSQL errors
        except psycopg2.Error as e:
            print(f"Database error during token validation: {e}")
            return jsonify({"message": "Database error during token validation"}), 500
        except Exception as e:
            print(f"Error during token decoding or user fetch: {e}")
            return jsonify({'message': 'Token processing error'}), 500

        return f(*args, **kwargs)
    return decorated

# --- API Routes (Use get_db for user operations) ---
@app.route('/api/register', methods=['POST'])
def register():
    """Registers a new user in the PostgreSQL database."""
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
    if len(password) < 6:
        return jsonify({"message": "Password must be at least 6 characters long"}), 400
    # --- End Validation ---


    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (fullname, email, password, count_completed, count_cancelled)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id""",
            (fullname, email, hashed_password, 0, 0)
        )
        user_id_row = cursor.fetchone()
        if user_id_row is None:
            raise Exception("User registration failed, could not retrieve new user ID.")
        user_id = user_id_row[0]

        conn.commit()
        cursor.close()
        print(f"User registered successfully with ID: {user_id}")
        return jsonify({"message": "User registered successfully", "userId": user_id}), 201

    except psycopg2.errors.UniqueViolation as e:
        if conn:
            conn.rollback()
        print(f"Registration failed: Email '{email}' already exists.")
        return jsonify({"message": "User already exists with this email"}), 409
    except (Exception, psycopg2.DatabaseError) as e:
        if conn:
            conn.rollback()
        print(f"Database error during registration: {e}")
        return jsonify({"message": "Database error during registration"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closing is handled by teardown_appcontext
        pass


@app.route('/api/login', methods=['POST'])
def login():
    """Logs a user in, returns JWT upon success."""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"message": "Missing username or password"}), 400

    # Assuming username field from frontend holds the email
    email = data['username']
    password = data['password']

    conn = None
    cursor = None
    try:
        conn = get_db()
        # Use DictCursor to access columns by name
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Use %s placeholder for PostgreSQL - Fetch user by email regardless of status first
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_row = cursor.fetchone() # Fetch one matching user

        # Important: Check if user_row exists before accessing its keys
        if user_row:
            # Check user status *before* checking password
            if user_row['status'] == 'blocked':
                print(f"Login attempt failed for blocked user: {email}")
                return jsonify({"message": "Your account is banned. Please check your email for more information!"}), 403 # Forbidden

            # If status is active, then check the password
            if user_row['status'] == 'active' and bcrypt.check_password_hash(user_row['password'], password):
                # User found, status is active, and password matches
                print(f"Login successful for user: {email} (ID: {user_row['id']})")

                # --- Generate JWT ---
                token = jwt.encode({
                    'user_id': user_row['id'],
                    'email': user_row['email'],
                    'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1) # Token expires in 1 hour
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
                # User exists, but password doesn't match (or status is not active, though handled above)
                print(f"Login failed for email: {email}. Incorrect password or inactive account.")
                return jsonify({"message": "Incorrect password."}), 401
        else: # User not found (email doesn't exist)
            print(f"Login failed for email: {email}. User not found.")
            return jsonify({"message": "Incorrect email address."}), 401

    # Catch PostgreSQL errors
    except psycopg2.Error as e:
        print(f"Database error during login: {e}")
        return jsonify({"message": "Database error during login"}), 500
    except Exception as e:
        # Catch other potential errors (like accessing user_row['password'] if user_row is None - though the check above prevents this)
        print(f"Unexpected error during login: {e}")
        return jsonify({"message": "An unexpected error occurred during login"}), 500
    finally:
        if cursor is not None:
            cursor.close() # Ensure cursor is closed
        # Connection closing is handled by teardown_appcontext
        pass



# --- Trade API Routes (Use get_db) ---

@app.route('/api/trades', methods=['GET'])
def get_trades():
    """Fetches trade data, optionally checking user's rating status if logged in."""
    conn = get_db()
    # Use DictCursor to access columns by name
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    current_user_id = None

    # --- Optional User Authentication ---
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        try:
            token = auth_header.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data.get('user_id')
            print(f"Token provided, user ID: {current_user_id}")
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, IndexError, KeyError):
            print("Invalid/Expired/Malformed token found, proceeding as guest.")
            pass
    # --- End Authentication Check ---

    # --- Get query parameters ---
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sortBy', 'name')
    sort_order = request.args.get('sortOrder', 'asc')

    # --- Validation ---
    # Note: 'business_name' is an alias for t.user_fullname, 'rating' is an alias for AVG(r.rating_score)
    allowed_sort_columns = ['name', 'price', 'user_fullname', 'place', 'rating', 'created_at']
    # Use actual column name `user_fullname` for sorting if `business_name` is selected
    db_sort_column = 'user_fullname' if sort_by == 'business_name' else sort_by
    if db_sort_column not in allowed_sort_columns:
        db_sort_column = 'name' # Default sort column
    if sort_order.lower() not in ['asc', 'desc']:
        sort_order = 'asc'

    # --- Build the SQL Query ---
    # Base selection (AVG is standard SQL)
    select_clause = """
        SELECT
            t.id, t.name, t.price, t.image, t.description, t.place, t.quantity,
            t.user_id AS seller_id,
            t.user_fullname AS business_name, -- Alias kept
            AVG(r.rating_score) as rating, -- Alias kept
             (SELECT AVG(sr.rating_score)
              FROM ratings sr
              WHERE sr.seller_id = t.user_id) as seller_average_rating
    """

    # FROM and JOIN clauses (LEFT JOIN is standard SQL)
    from_join_clause = """
        FROM trades t
        LEFT JOIN ratings r ON t.id = r.trade_id
    """

    # GROUP BY is needed for AVG()
    group_by_clause = " GROUP BY t.id "
    # Use the potentially modified db_sort_column
    order_by_clause = f" ORDER BY {db_sort_column} {sort_order.upper()}"

    where_clauses = []
    where_params = [] # Separate params for WHERE clause

    # Add search condition - Use %s placeholders and ILIKE for case-insensitive search
    if search_query:
        search_term = f'%{search_query}%'
        # Use ILIKE for case-insensitive matching in PostgreSQL
        search_condition = """(
            t.name ILIKE %s OR
            t.description ILIKE %s OR
            t.place ILIKE %s OR
            t.user_fullname ILIKE %s
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
    final_params = tuple(where_params) # Ensure it's a tuple, removed params for user_id

    # --- End Build SQL Query ---

    try:
        print(f"Executing SQL: {sql}")
        print(f"With params: {final_params}")
        cursor.execute(sql, final_params)
        # Fetchall with DictCursor returns a list of DictRow objects
        trades_raw = cursor.fetchall()
        trades = [dict(row) for row in trades_raw] # Convert DictRows to plain dicts for jsonify

        # --- Type Conversion (Keep existing logic, adjust if needed) ---
        # PostgreSQL might return Decimal for REAL, ensure float conversion
        for trade in trades:
             if trade.get('price') is not None: trade['price'] = float(trade['price'])
             # AVG returns Decimal, convert to float
             if trade.get('rating') is not None: trade['rating'] = float(trade['rating'])
             if trade.get('seller_average_rating') is not None:
                trade['seller_average_rating'] = float(trade['seller_average_rating'])
             # quantity (INTEGER) and seller_id (INTEGER) should be fine

        cursor.close()
        return jsonify(trades)
    # Catch PostgreSQL errors
    except psycopg2.Error as e:
        print(f"Database error fetching trades: {e}")
        # Optionally rollback if the transaction state is unknown, though usually SELECTs don't need it
        # conn.rollback()
        return jsonify({"message": "Error fetching trade data"}), 500
    except Exception as e:
        print(f"Error fetching trades: {e}")
        return jsonify({"message": "Could not retrieve trade data"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closing is handled by teardown_appcontext
        pass


@app.route('/api/trades', methods=['POST'])
@token_required # Protect this route
def add_trade():
    """Adds a new trade item to the PostgreSQL database linked to the logged-in user."""
    # Ensure user is authenticated and get user info from g
    # The @token_required decorator should have populated g.current_user
    if not hasattr(g, 'current_user') or not g.current_user:
        return jsonify({"message": "Authentication required or user data missing from context"}), 401
    user_id = g.current_user['id']
    user_fullname = g.current_user['fullname']

    data = request.get_json()

    # --- Validation --- # (Keep existing validation logic)
    if not data or not data.get('name') or data.get('price') is None:
        return jsonify({"message": "Missing required fields (name, price)"}), 400

    name = data['name']
    price_str = str(data['price']).strip()
    image = data.get('image', None)
    description = data.get('description', None)
    place = data.get('place', None)
    try:
        quantity = int(data.get('quantity', 1))
        if quantity < 0: # Enforce non-negative quantity
             return jsonify({"message": "Quantity cannot be negative"}), 400 # Handle as error
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid quantity format. Please enter a number."}), 400

    try:
        price = float(price_str)
        if price < 0:
             return jsonify({"message": "Price cannot be negative"}), 400
    except ValueError:
        return jsonify({"message": "Invalid price format. Please enter a number."}), 400
    # --- End Validation ---

    conn = None # Initialize conn
    cursor = None
    trade_id = None # Initialize trade_id
    try:
        conn = get_db() # Use PostgreSQL connection
        # Use DictCursor to fetch the newly added row easily later
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Use %s placeholders and RETURNING id
        cursor.execute(
            """INSERT INTO trades (name, price, image, description, place, user_id, user_fullname, quantity)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (name, price, image, description, place, user_id, user_fullname, quantity)
        )
        # Fetch the returned id
        trade_id_row = cursor.fetchone()
        if trade_id_row is None:
             raise Exception("Trade insertion failed, could not retrieve new trade ID.")
        trade_id = trade_id_row['id'] # Access by name with DictCursor

        # Commit the transaction *after* successful insert and ID retrieval
        conn.commit()

        # Fetch the newly created trade to return its details
        # Re-use the cursor after commit (it's still valid within the connection)
        cursor.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
        new_trade_row = cursor.fetchone()

        print(f"Trade item '{name}' (ID: {trade_id}) added by user {user_fullname} (ID: {user_id}).")
        return jsonify({
            "message": "Trade added successfully",
            "tradeId": trade_id,
            "trade": dict(new_trade_row) if new_trade_row else None
            }), 201 # 201 Created

    # Catch PostgreSQL errors
    except (Exception, psycopg2.DatabaseError) as e:
        if conn:
            conn.rollback() # Rollback the transaction on any error
        print(f"Database error adding trade: {e}")
        # Check if it's a check constraint violation (e.g., negative quantity)
        if isinstance(e, psycopg2.errors.CheckViolation):
             return jsonify({"message": f"Data validation failed: {e}"}), 400
        return jsonify({"message": "Database error adding trade"}), 500
    finally:
        if cursor is not None:
            cursor.close() # Ensure cursor is closed
        # Connection closing is handled by teardown_appcontext
        pass

# --- Cart API Routes ---

@app.route('/api/cart', methods=['POST'])
@token_required
def add_to_cart():
    """Adds a trade item to the user's cart.
    If a 'pending' item for this user/trade exists, updates its quantity.
    Otherwise, creates a new 'pending' cart item.
    """
    user_id = g.current_user['id']
    data = request.get_json()

    if not data or 'trade_id' not in data:
        return jsonify({"message": "Missing 'trade_id' in request body"}), 400

    trade_id = data['trade_id']
    try:
        quantity_to_add = int(data.get('quantity', 1))
        if quantity_to_add <= 0:
            return jsonify({"message": "Quantity to add must be positive"}), 400
    except (ValueError, TypeError):
         return jsonify({"message": "Invalid quantity format"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Check trade exists, stock, and seller is not buyer
        cursor.execute("SELECT quantity, user_id as seller_id FROM trades WHERE id = %s", (trade_id,))
        trade_info = cursor.fetchone()
        if not trade_info:
             return jsonify({"message": f"Trade item with ID {trade_id} not found"}), 404

        available_stock = trade_info['quantity']
        if trade_info['seller_id'] == user_id:
            return jsonify({"message": "You cannot add your own listing to the cart"}), 400

        # 2. Look for an existing *pending* cart item for this user and trade
        cursor.execute(
            "SELECT id, quantity FROM cart_items WHERE user_id = %s AND trade_id = %s AND status = 'pending'",
            (user_id, trade_id)
        )
        pending_item = cursor.fetchone()

        if pending_item:
            # 3a. Found a pending item - try to update its quantity
            existing_cart_id = pending_item['id']
            current_cart_qty = pending_item['quantity']
            potential_new_cart_qty = current_cart_qty + quantity_to_add

            if potential_new_cart_qty > available_stock:
                 remaining_can_add = available_stock - current_cart_qty
                 return jsonify({
                    "message": f"Cannot add {quantity_to_add}. Only {available_stock} available. Your pending cart item already has {current_cart_qty}." +
                               (f" You can add at most {remaining_can_add} more." if remaining_can_add >= 0 else " No more can be added.")
                 }), 400

            # Update existing pending item's quantity
            cursor.execute(
                "UPDATE cart_items SET quantity = %s WHERE id = %s",
                (potential_new_cart_qty, existing_cart_id)
            )
            conn.commit()
            print(f"Updated quantity for pending cart item {existing_cart_id}")
            # Fetch the updated item to return details
            cursor.execute("SELECT id as cart_item_id, trade_id, quantity, status FROM cart_items WHERE id = %s", (existing_cart_id,))
            updated_item = cursor.fetchone()
            return jsonify({
                "message": "Quantity updated for pending item in cart",
                "item": dict(updated_item) if updated_item else None
            }), 200

        else:
            # 3b. No *pending* item found for this user/trade - create a new one
            # Check stock just for the quantity being added now
            if quantity_to_add > available_stock:
                 return jsonify({
                    "message": f"Cannot add {quantity_to_add}. Only {available_stock} available."
                 }), 400

            # Insert new cart item
            cursor.execute(
                """INSERT INTO cart_items (user_id, trade_id, quantity, status)
                   VALUES (%s, %s, %s, 'pending')
                   RETURNING id as cart_item_id, trade_id, quantity, status""",
                (user_id, trade_id, quantity_to_add)
            )
            new_item = cursor.fetchone()
            conn.commit()
            print(f"Inserted new cart item {new_item['cart_item_id']}")
            return jsonify({
                "message": "New item added to cart",
                "item": dict(new_item) if new_item else None
            }), 201 # 201 Created for new resource


    except (Exception, psycopg2.DatabaseError) as e:
        if conn:
            conn.rollback()
        print(f"Database error adding to cart: {e}")
        # Check for specific stock-related constraint errors if any exist
        return jsonify({"message": "Database error adding to cart"}), 500
    finally:
        if cursor is not None:
            cursor.close()


@app.route('/api/cart', methods=['GET'])
@token_required
def get_cart():
    """Gets all individual items in the user's cart with trade details.
       Handles cases where multiple cart items might exist for the same trade_id (different statuses).
    """
    user_id = g.current_user['id']
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Fetch ALL cart items for the user
        cursor.execute(
            """SELECT 
                   ci.id as cart_item_id, 
                   ci.trade_id, 
                   ci.quantity, 
                   ci.status, 
                   r.rating_score AS user_rating_for_item -- Get rating linked to this cart item
               FROM cart_items ci
               LEFT JOIN ratings r ON ci.id = r.cart_item_id AND r.user_id = %s -- Join rating for this user and cart item
               WHERE ci.user_id = %s 
               ORDER BY ci.added_at ASC""",
            (user_id, user_id) # user_id needed twice: once for rating join, once for WHERE clause
        )
        user_cart_items_raw = cursor.fetchall()

        if not user_cart_items_raw:
            cursor.close()
            return jsonify({"cart": []}), 200 # Return empty cart

        # 2. Get unique trade IDs from the cart items
        trade_ids = list(set(item['trade_id'] for item in user_cart_items_raw)) # Use set for uniqueness

        # 3. Fetch details for these unique trades (excluding seller and user rating now)
        trade_details_map = {}
        if trade_ids: # Proceed only if there are trade IDs
            query = """
                SELECT
                    t.id, t.name, t.price, t.quantity AS trade_quantity, t.image,
                    t.user_id AS seller_id, t.user_fullname AS business_name,
                    t.description AS trade_description, t.place AS trade_place,
                    u.email AS seller_email
                FROM trades t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = ANY(%s) -- Use ANY() for list parameter with IN operator in psycopg2
            """
            cursor.execute(query, (trade_ids,)) # Execute without user_id parameter for rating
            trade_details_list = cursor.fetchall()
            # Convert list of trade details into a dictionary mapped by trade_id
            trade_details_map = {trade['id']: dict(trade) for trade in trade_details_list}

        # 4. Combine cart item specifics with trade details
        final_cart_items = []
        for cart_item_row in user_cart_items_raw:
            cart_item = dict(cart_item_row)
            trade_id = cart_item['trade_id']

            # Get the base trade details from the map
            base_trade_details = trade_details_map.get(trade_id)

            if base_trade_details:
                # Create a new dictionary for this specific cart item instance
                combined_item = base_trade_details.copy() # Start with trade details

                # Override/Add specific cart item details
                combined_item['cart_item_id'] = cart_item['cart_item_id']
                combined_item['quantity'] = cart_item['quantity'] # This is the quantity IN THE CART
                combined_item['cart_status'] = cart_item['status']
                # Use the rating fetched specifically for this cart item
                combined_item['current_user_rating_score'] = cart_item.get('user_rating_for_item')

                final_cart_items.append(combined_item)
            else:
                # Handle case where trade details might be missing (e.g., trade deleted after adding to cart)
                print(f"Warning: Trade details not found for trade_id {trade_id} referenced by cart_item_id {cart_item['cart_item_id']}")
                # Optionally, you could add a placeholder item or skip it
                # final_cart_items.append({
                #     'cart_item_id': cart_item['cart_item_id'],
                #     'trade_id': trade_id,
                #     'quantity': cart_item['quantity'],
                #     'cart_status': cart_item['status'],
                #     'name': '[Trade Deleted]',
                #     'price': 0
                #     # Add other necessary fields as defaults or nulls
                # })

        cursor.close()
        return jsonify({"cart": final_cart_items}), 200

    # Catch PostgreSQL errors
    except psycopg2.Error as e:
        print(f"Database error fetching cart: {e}")
        return jsonify({"message": "Error fetching cart data"}), 500
    except Exception as e:
        print(f"Unexpected error fetching cart: {e}")
        return jsonify({"message": "An unexpected error occurred fetching cart data"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection is closed by teardown context
        pass


@app.route('/api/cart/items/<int:cart_item_id>', methods=['DELETE']) # MODIFIED: Changed route and parameter name
@token_required
def remove_from_cart(cart_item_id): # MODIFIED: Changed parameter name
    """Removes a specific item from the user's cart using the cart_item_id."""
    user_id = g.current_user['id']
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) # Use DictCursor to check user_id

        # MODIFIED: Find item by cart_item_id first
        cursor.execute(
            "SELECT user_id FROM cart_items WHERE id = %s",
            (cart_item_id,)
        )
        item = cursor.fetchone()

        if not item:
            return jsonify({"message": f"Cart item with ID {cart_item_id} not found"}), 404

        # MODIFIED: Verify the item belongs to the current user
        if item['user_id'] != user_id:
            return jsonify({"message": "Not authorized to remove this item"}), 403

        # Proceed with deletion using cart_item_id
        cursor.execute(
            "DELETE FROM cart_items WHERE id = %s", # MODIFIED: WHERE clause uses id
            (cart_item_id,)
        )
        conn.commit()

        if cursor.rowcount > 0:
            print(f"Cart item {cart_item_id} removed from cart for user {user_id}.")
            return jsonify({"message": f"Cart item {cart_item_id} removed"}), 200
        else:
            # This case should technically not be reached if the initial find was successful
            print(f"Attempted to remove cart item {cart_item_id} for user {user_id}, but deletion failed (rowcount 0).")
            return jsonify({"message": "Item removal failed unexpectedly"}), 500

    # Catch PostgreSQL errors
    except (Exception, psycopg2.DatabaseError) as e:
        if conn:
            conn.rollback()
        print(f"Database error removing from cart: {e}")
        return jsonify({"message": "Database error removing from cart"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection is closed by teardown context
        pass

# --- New endpoint for buyer to mark a cart item as 'ordered' ---
@app.route('/api/cart/items/<int:cart_item_id>/order', methods=['POST']) # MODIFIED: Changed route and parameter name
@token_required
def order_cart_item(cart_item_id): # MODIFIED: Changed parameter name
    """Updates the status of a specific item in the user's cart to 'ordered' using cart_item_id."""
    user_id = g.current_user['id']
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Check if the item exists in the cart and get its details (including trade_id and user_id)
        # MODIFIED: Find by cart_item_id
        cursor.execute(
            "SELECT id, user_id, trade_id, quantity, status FROM cart_items WHERE id = %s",
            (cart_item_id,)
        )
        cart_item = cursor.fetchone()

        if not cart_item:
            return jsonify({"message": f"Cart item {cart_item_id} not found."}), 404

        # MODIFIED: Verify the item belongs to the current user
        if cart_item['user_id'] != user_id:
            return jsonify({"message": "Not authorized to modify this item"}), 403

        # 2. Check if the item is already ordered or in another final state
        if cart_item['status'] not in ['pending']: # Only allow ordering from pending state
            return jsonify({"message": f"Item status is '{cart_item['status']}'. Cannot place order."}), 400

        ordered_quantity = cart_item['quantity'] # Quantity from the cart
        trade_id = cart_item['trade_id'] # MODIFIED: Get trade_id from the fetched cart item

        # 3. Check available stock from trades DB
        # Use the same cursor and %s placeholder
        cursor.execute("SELECT quantity FROM trades WHERE id = %s", (trade_id,))
        trade = cursor.fetchone()

        if not trade:
             # Trade might have been deleted since added to cart
             return jsonify({"message": f"Associated trade item {trade_id} no longer exists."}), 404

        available_stock = trade['quantity']

        if ordered_quantity > available_stock:
            return jsonify({
                "message": f"Insufficient stock. Only {available_stock} available, you tried to order {ordered_quantity}.",
                "available": available_stock
                 }), 400 # Bad Request - insufficient stock

        # 4. Update the status to 'ordered' if stock is sufficient
        # MODIFIED: Use cart_item_id in WHERE clause
        cursor.execute(
            "UPDATE cart_items SET status = 'ordered' WHERE id = %s",
            (cart_item_id,) # Use the cart_item PK for precision
        )

        # Check if the update was successful before committing
        if cursor.rowcount == 0:
            # Should not happen if first checks passed, but for safety
            raise Exception(f"Failed to update cart item status for ID {cart_item_id} (rowcount 0).")

        conn.commit()

        print(f"Cart item {cart_item_id} (trade_id: {trade_id}) marked as ordered by user {user_id}.")
        return jsonify({"message": "Item successfully ordered", "new_status": "ordered"}), 200

    # Catch PostgreSQL specific and general errors
    except psycopg2.Error as e:
        if conn: conn.rollback()
        print(f"Database error updating cart item status: {e}")
        return jsonify({"message": "Database error updating cart item status"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error updating cart item status: {e}")
        return jsonify({"message": "An unexpected error occurred"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

# --- Profile Stats Route (Updated) ---

@app.route('/api/profile/stats', methods=['GET'])
@token_required
def get_profile_stats():
    """Gets user's listed items, overall seller rating, and success percentage."""
    user_id = g.current_user['id']
    conn = None
    cursor = None
    seller_avg_rating = None
    listings = []
    count_completed = 0
    count_cancelled = 0
    successful_trade_percentage = 0

    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Fetch all trades listed by the user (with average product rating)
        # Use %s placeholder
        cursor.execute(
            """SELECT t.id, t.name, t.price, t.quantity, t.image, t.description, t.place, t.created_at,
                      AVG(r.rating_score) as average_product_rating
               FROM trades t
               LEFT JOIN ratings r ON t.id = r.trade_id
               WHERE t.user_id = %s
               GROUP BY t.id
               ORDER BY t.created_at ASC""",
            (user_id,)
        )
        listings_raw = cursor.fetchall()
        listings = []
        for row in listings_raw:
            item = dict(row)
            # Ensure numeric types are correct
            if item.get('price') is not None: item['price'] = float(item['price'])
            if item.get('quantity') is not None: item['quantity'] = int(item['quantity'])
            if item.get('average_product_rating') is not None: item['average_product_rating'] = float(item['average_product_rating'])

            # Determine status based on quantity
            item['status'] = 'Available' if item['quantity'] > 0 else 'Out of stock'
            listings.append(item)

        # 2. Calculate the overall average rating for the SELLER using the new seller_id column
        # Use %s placeholder
        cursor.execute(
            """SELECT AVG(rating_score)
               FROM ratings
               WHERE seller_id = %s""", # <<< NEW QUERY
            (user_id,)
        )
        avg_result = cursor.fetchone()
        # Result might be Decimal, handle None and convert to float
        if avg_result and avg_result[0] is not None:
            seller_avg_rating = round(float(avg_result[0]), 2)

        # 3. Fetch completion/cancellation counts from users table
        # Use the same cursor and %s placeholder
        cursor.execute(
            "SELECT count_completed, count_cancelled FROM users WHERE id = %s",
            (user_id,)
        )
        user_counts = cursor.fetchone()
        if user_counts:
            count_completed = user_counts['count_completed']
            count_cancelled = user_counts['count_cancelled']

        # 4. Calculate successful trade percentage
        total_finalized = count_completed + count_cancelled
        if total_finalized > 0:
             successful_trade_percentage = round((count_completed / total_finalized) * 100, 1)

        cursor.close()
        return jsonify({
            "listings": listings,
            "seller_average_rating": seller_avg_rating,
            "successful_trades_percentage": successful_trade_percentage
            }), 200

    # Catch PostgreSQL errors
    except psycopg2.Error as e:
        print(f"Database error fetching profile stats: {e}")
        return jsonify({"message": "Error fetching profile statistics"}), 500
    except Exception as e:
        print(f"Unexpected error fetching profile stats: {e}")
        return jsonify({"message": "An unexpected error occurred fetching profile stats"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

# --- Export Route (New) ---
@app.route('/api/trades/export', methods=['GET'])
@token_required # Add token requirement
def export_trades_csv():
    """Exports all trade data to a CSV file. Intended for admin use."""

    conn = None
    cursor = None
    try:
        conn = get_db() # Use PostgreSQL connection
        cursor = conn.cursor() # Standard cursor is fine
        # SQL query should be compatible with PostgreSQL
        cursor.execute("SELECT id, name, price, quantity, image, description, place, user_id, user_fullname, created_at FROM trades ORDER BY created_at ASC")
        trades = cursor.fetchall()

        # Use StringIO to create CSV in memory (No change needed here)
        si = StringIO()
        cw = csv.writer(si)

        # Write Header (No change needed here)
        column_names = [description[0] for description in cursor.description]
        cw.writerow(column_names)

        # Write Data Rows (No change needed here)
        cw.writerows(trades)

        # Prepare response (No change needed here)
        output = si.getvalue()
        si.close()

        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-disposition":
                     "attachment; filename=trades_export.csv"}
        )

    # Catch PostgreSQL errors
    except psycopg2.Error as e:
        print(f"Database error during CSV export: {e}")
        return jsonify({"message": "Error exporting trade data"}), 500
    except Exception as e:
        print(f"General error during CSV export: {e}")
        return jsonify({"message": "Could not generate trade export"}), 500
    finally:
        if cursor is not None:
            cursor.close() # Ensure cursor is closed
        # Connection closed by teardown context
        pass

# --- New Trade Action Endpoints ---

@app.route('/api/cart/items/<int:cart_item_id>/rate', methods=['POST']) # MODIFIED: Route uses cart_item_id
@token_required
def rate_trade(cart_item_id): # MODIFIED: Parameter is cart_item_id
    """Rates a specific completed order instance (cart item)."""
    data = request.get_json()
    if not data or 'rating_score' not in data:
        return jsonify({"message": "Rating score is required"}), 400

    try:
        # Validate rating score (must be integer 1-5)
        rating_score = int(data['rating_score'])
        if not (1 <= rating_score <= 5):
             raise ValueError("Rating score must be between 1 and 5")
    except (ValueError, TypeError):
         return jsonify({"message": "Invalid rating score (must be an integer between 1 and 5)"}), 400

    user_id = g.current_user['id'] # User performing the rating (Buyer)

    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # --- Rating Restrictions based on Cart Item ID --- 
        # 1. Fetch the specific cart item
        cursor.execute(
            "SELECT user_id, trade_id, status FROM cart_items WHERE id = %s", 
            (cart_item_id,)
        )
        cart_item = cursor.fetchone()

        if not cart_item:
            return jsonify({"message": "Order item not found"}), 404

        # 2. Verify the rater is the buyer for this specific cart item
        if cart_item['user_id'] != user_id:
            return jsonify({"message": "You can only rate orders you placed"}), 403 # Forbidden

        # 3. Check if this specific order item is completed
        if cart_item['status'] != 'completed':
            return jsonify({"message": f"You can only rate completed orders (current status: '{cart_item['status']}')"}), 400

        trade_id = cart_item['trade_id'] # Get the trade_id associated with this cart item

        # 4. Optional: Double-check rater isn't the seller (unlikely if previous check passed, but safe)
        cursor.execute("SELECT user_id FROM trades WHERE id = %s", (trade_id,))
        trade = cursor.fetchone()
        if not trade:
             return jsonify({"message": "Associated trade not found (may have been deleted)"}), 404
        
        seller_id = trade['user_id'] # This is the ID of the user who listed the trade
        # Optional: Double-check rater isn't the seller (already done implicitly by fetching trade)
        if seller_id == user_id:
             return jsonify({"message": "Sellers cannot rate their own trades/orders"}), 403
        # --- End Rating Restrictions ---

        # --- Insert or Replace the rating in the 'ratings' table, including seller_id --- 
        cursor.execute("""
            INSERT INTO ratings (trade_id, user_id, seller_id, cart_item_id, rating_score)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (cart_item_id) DO UPDATE SET
                rating_score = excluded.rating_score,
                seller_id = excluded.seller_id, -- Also update seller_id on conflict if needed
                rated_at = CURRENT_TIMESTAMP
        """, (trade_id, user_id, seller_id, cart_item_id, rating_score)) # Added seller_id here
        # --- End Insert/Replace ---

        conn.commit() 
        return jsonify({"message": "Rating submitted successfully"}), 200

    # Catch PostgreSQL errors
    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        print(f"Integrity error rating trade: {e}")
        # Provide a slightly more generic message to the user
        return jsonify({"message": f"Could not submit rating due to a data conflict."}), 409
    except psycopg2.Error as e:
        if conn: conn.rollback()
        print(f"Database error rating trade: {e}")
        return jsonify({"message": "Database error processing rating"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error rating trade: {e}")
        return jsonify({"message": "Error processing rating"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

# --- New endpoint to delete a trade ---
@app.route('/api/trades/<int:trade_id>', methods=['DELETE'])
@token_required
def delete_trade(trade_id):
    """Deletes a trade item and associated cart items if the logged-in user is the seller."""
    user_id = g.current_user['id']
    conn = None
    cursor = None
    deleted_cart_count = 0
    deleted_trade_count = 0

    try:
        conn = get_db()
        # Use DictCursor for the initial check
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Verify the trade exists and the current user is the seller
        # Use %s placeholder
        cursor.execute("SELECT user_id FROM trades WHERE id = %s", (trade_id,))
        trade = cursor.fetchone()
        cursor.close() # Close this cursor after initial check

        if not trade:
            return jsonify({"message": "Trade not found"}), 404

        if trade['user_id'] != user_id:
            return jsonify({"message": "You are not authorized to delete this trade"}), 403 # Forbidden


        # 2. Start Transaction and perform deletions
        cursor = conn.cursor() # Re-open standard cursor for DELETE

        # Delete associated cart items - Use %s
        cursor.execute("DELETE FROM cart_items WHERE trade_id = %s", (trade_id,))
        deleted_cart_count = cursor.rowcount # Get count *before* deleting the trade
        print(f"Deleted {deleted_cart_count} associated cart items for trade {trade_id}.")

        # Delete the trade itself - Use %s
        cursor.execute("DELETE FROM trades WHERE id = %s", (trade_id,))
        deleted_trade_count = cursor.rowcount

        if deleted_trade_count == 0:
            # This shouldn't happen if initial check passed, but indicates an issue.
            # Rollback because the primary deletion failed.
            conn.rollback()
            print(f"ERROR: Trade {trade_id} not found during deletion attempt after initial check.")
            return jsonify({"message": "Trade deletion failed unexpectedly after initial check."}), 500

        # 3. Commit the transaction if both deletions were successful (or cart delete didn't error)
        conn.commit()

        print(f"Trade {trade_id} deleted successfully by user {user_id}.")
        return jsonify({"message": "Trade deleted successfully", "deleted_cart_items": deleted_cart_count}), 200

    # Catch PostgreSQL errors
    except psycopg2.Error as db_e:
        if conn:
            conn.rollback() # Rollback transaction on any DB error
        print(f"Database error during trade deletion process for trade {trade_id}: {db_e}")
        return jsonify({"message": "Database error during trade deletion"}), 500
    except Exception as e:
        # Catch any other unexpected errors
        if conn:
            conn.rollback()
        print(f"Unexpected error deleting trade {trade_id}: {e}")
        return jsonify({"message": "An unexpected error occurred while deleting the trade"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass



# --- New endpoint to UPDATE a trade ---
@app.route('/api/trades/<int:trade_id>', methods=['PUT'])
@token_required
def update_trade(trade_id):
    """Updates an existing trade item if the logged-in user is the seller."""
    user_id = g.current_user['id']
    conn = None
    cursor = None

    # 1. Verify the trade exists and the current user is the seller
    try:
        conn = get_db()
        # Use DictCursor for initial check
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Use %s placeholder
        cursor.execute("SELECT user_id FROM trades WHERE id = %s", (trade_id,))
        trade = cursor.fetchone()
        cursor.close() # Close this cursor after initial check

        if not trade:
            return jsonify({"message": "Trade not found"}), 404

        if trade['user_id'] != user_id:
            return jsonify({"message": "You are not authorized to update this trade"}), 403

    except psycopg2.Error as e:
        print(f"Database error verifying trade {trade_id} for update: {e}")
        return jsonify({"message": "Database error checking trade before update"}), 500
    # Close connection here if initial check fails? No, teardown handles it.

    # 2. Get updated data from request body
    data = request.get_json()
    if not data:
        return jsonify({"message": "No update data provided"}), 400

    # 3. Build the SET part of the SQL query dynamically
    fields_to_update = {}
    allowed_fields = ['name', 'price', 'quantity', 'image', 'description', 'place']

    for field in allowed_fields:
        if field in data:
            # Validation
            if field == 'price':
                try:
                    price = float(data[field])
                    if price < 0:
                         return jsonify({"message": "Price cannot be negative"}), 400
                    fields_to_update[field] = price
                except (ValueError, TypeError):
                    return jsonify({"message": "Invalid price format"}), 400
            elif field == 'quantity':
                 try:
                    quantity = int(data[field])
                    if quantity < 0:
                         return jsonify({"message": "Quantity cannot be negative"}), 400
                    fields_to_update[field] = quantity
                 except (ValueError, TypeError):
                    return jsonify({"message": "Invalid quantity format"}), 400
            elif field == 'name' and not str(data[field]).strip(): # Ensure name is not empty string
                 return jsonify({"message": "Name cannot be empty"}), 400
            else:
                fields_to_update[field] = data[field]

    if not fields_to_update:
        return jsonify({"message": "No valid fields provided for update"}), 400

    # Construct the SET clause and parameter list using %s
    set_clause = ", ".join([f"{field} = %s" for field in fields_to_update])
    params = list(fields_to_update.values())
    params.append(trade_id) # Add trade_id for the WHERE clause

    sql = f"UPDATE trades SET {set_clause} WHERE id = %s"

    # 4. Execute the update
    cursor = None # Reset cursor variable
    try:
        # Re-use connection, get new DictCursor for fetching updated row
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(sql, tuple(params))

        if cursor.rowcount == 0:
            # Should not happen if initial check passed, but indicates an issue.
            conn.rollback() # Rollback just in case
            print(f"ERROR: Trade {trade_id} update failed (rowcount 0) after initial check.")
            return jsonify({"message": "Trade update failed unexpectedly."}), 500

        # Fetch the updated trade to return it
        cursor.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
        updated_trade = cursor.fetchone()

        # Commit transaction *after* successful update and fetch
        conn.commit()

        print(f"Trade {trade_id} updated successfully by user {user_id}.")
        return jsonify({
            "message": "Trade updated successfully",
            "trade": dict(updated_trade) if updated_trade else None
        }), 200

    # Catch PostgreSQL errors
    except psycopg2.Error as e:
        if conn: conn.rollback()
        print(f"Database error updating trade {trade_id}: {e}")
        if isinstance(e, psycopg2.errors.CheckViolation):
             return jsonify({"message": f"Data validation failed: {e}"}), 400
        return jsonify({"message": "Database error updating trade"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error updating trade {trade_id}: {e}")
        return jsonify({"message": "An unexpected error occurred while updating the trade"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass



# --- New endpoint to get incoming orders for the logged-in seller ---
@app.route('/api/profile/incoming_orders', methods=['GET'])
@token_required
def get_incoming_orders():
    """Gets items listed by the seller that buyers have acted upon (ordered, accepted, paid).""" # Updated docstring
    seller_id = g.current_user['id']
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Use standard JOINs now that all tables are in the same DB
        # Use %s placeholder
        query = """
            SELECT
                ci.id AS cart_item_id,
                ci.quantity AS ordered_quantity,
                ci.added_at AS ordered_at, -- Might want to rename this alias if confusing
                ci.status, -- Select the status
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
                users b ON ci.user_id = b.id -- Join buyer details from users table (aliased b)
            JOIN
                trades t ON ci.trade_id = t.id -- Join trade details from trades table (aliased t)
            WHERE
                t.user_id = %s -- Filter: Trade belongs to the logged-in seller
                -- AND ci.status = 'ordered' -- Old Filter: REMOVE OR COMMENT OUT
                AND ci.status IN ('ordered', 'accepted', 'payment_confirmed') -- CORRECTED FILTER
            ORDER BY
                ci.added_at ASC; -- Show oldest orders first
        """
        cursor.execute(query, (seller_id,))
        incoming_orders_raw = cursor.fetchall()
        # --- Add Logging Here --- 
        print(f"[GET INCOMING ORDERS] Raw data fetched for seller {seller_id}: {incoming_orders_raw}")
        # --- End Logging --- 

        incoming_orders = [dict(row) for row in incoming_orders_raw]

        # Ensure numeric types are correct (price)
        for item in incoming_orders:
            if item.get('trade_price') is not None: item['trade_price'] = float(item['trade_price'])

        cursor.close()
        return jsonify({"incoming_orders": incoming_orders}), 200

    # Catch PostgreSQL errors
    except psycopg2.Error as e:
        print(f"Database error fetching incoming orders: {e}")
        return jsonify({"message": "Error fetching incoming orders"}), 500
    except Exception as e:
        print(f"Unexpected error fetching incoming orders: {e}")
        return jsonify({"message": "An unexpected error occurred fetching incoming orders"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

# --- New endpoints for seller to accept/decline orders ---

@app.route('/api/seller/orders/accept', methods=['POST'])
@token_required
def seller_accept_order():
    """Allows seller to accept an 'ordered' cart item.
       Updates cart status, increments seller's completed count, and decrements trade stock.
       Uses a single transaction for atomicity.
    """
    seller_id = g.current_user['id']
    data = request.get_json()

    if not data or 'cart_item_id' not in data:
        return jsonify({"message": "Missing 'cart_item_id' in request body"}), 400

    cart_item_id = data['cart_item_id']

    conn = None
    cursor = None
    try:
        conn = get_db()
        # Use DictCursor for easier access during checks
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # --- Initial Checks (Read-only operations) ---
        print(f"[ACCEPT ORDER] Seller ID from token: {seller_id}") # Log seller ID from token
        print(f"[ACCEPT ORDER] Received cart_item_id: {cart_item_id}") # Log received cart_item_id

        # 1. Fetch cart item and verify status
        cursor.execute(
            "SELECT user_id, trade_id, quantity, status FROM cart_items WHERE id = %s",
            (cart_item_id,)
        )
        cart_item = cursor.fetchone()

        if not cart_item:
            return jsonify({"message": "Cart item not found"}), 404
            
        trade_id = cart_item['trade_id']
        ordered_quantity = cart_item['quantity']
        print(f"[ACCEPT ORDER] Fetched trade_id from cart_item: {trade_id}") # Log fetched trade_id

        # Check if the status is correct *before* fetching trade details
        if cart_item['status'] != 'ordered':
            return jsonify({"message": f"Cannot accept order. Current status: {cart_item['status']}"}), 400

        # 2. Fetch trade details, verify seller ownership and stock
        cursor.execute(
            "SELECT user_id, quantity FROM trades WHERE id = %s",
            (trade_id,)
        )
        trade = cursor.fetchone()

        if not trade:
            return jsonify({"message": "Associated trade not found"}), 404
            
        original_seller_id = trade['user_id']
        print(f"[ACCEPT ORDER] Original seller ID from trade table: {original_seller_id}") # Log original seller_id from trade
        
        # Authorization check
        if original_seller_id != seller_id:
            print(f"[ACCEPT ORDER] Authorization failed: Token seller ({seller_id}) != Trade seller ({original_seller_id})") # Log auth failure
            return jsonify({"message": "Not authorized to manage this item"}), 403
        
        # Stock check
        if trade['quantity'] < ordered_quantity:
            return jsonify({
                "message": f"Insufficient stock ({trade['quantity']}) to fulfill ordered quantity ({ordered_quantity})."
            }), 400


        # 3. Update cart item status to 'accepted' (was 'completed')
        cursor.execute(
            "UPDATE cart_items SET status = 'accepted' WHERE id = %s",
            (cart_item_id,)
        )
        if cursor.rowcount == 0:
             raise psycopg2.Error("Failed to update cart item status to accepted")

        # If all updates were successful, commit the transaction
        conn.commit()
        print(f"Order accepted (awaiting payment) and committed for cart_item {cart_item_id} by seller {seller_id}.") # Updated log message
        return jsonify({"message": "Order accepted successfully, awaiting payment"}), 200 # Updated success message

    # Catch ALL PostgreSQL errors during the process
    except psycopg2.Error as db_e:
        if conn:
            conn.rollback() # Rollback the entire transaction on any DB error
        print(f"Database error during order acceptance process for cart_item {cart_item_id}: {db_e}")
        # Provide a more specific message if it's about stock mismatch (though unlikely with prior check)
        if "Failed to decrement stock" in str(db_e):
             return jsonify({"message": "Stock level changed before update could complete. Please try again or decline."}), 409 # Conflict
        return jsonify({"message": "Database error processing acceptance request"}), 500
    except Exception as e:
        # Catch any other unexpected errors
        if conn:
            conn.rollback()
        print(f"Unexpected error accepting order: {e}")
        return jsonify({"message": "An unexpected error occurred"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

@app.route('/api/seller/orders/decline', methods=['POST'])
@token_required
def seller_decline_order():
    """Allows seller to decline an 'ordered' cart item.
       Updates cart status to 'cancelled' and increments seller's cancelled count.
       Uses a single transaction.
    """
    seller_id = g.current_user['id']
    data = request.get_json()

    if not data or 'cart_item_id' not in data:
        return jsonify({"message": "Missing 'cart_item_id' in request body"}), 400

    cart_item_id = data['cart_item_id']

    conn = None
    cursor = None
    try:
        conn = get_db()
        # Use DictCursor for initial checks
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # --- Initial Checks ---
        # 1. Fetch cart item and verify status
        cursor.execute(
            "SELECT user_id, trade_id, status FROM cart_items WHERE id = %s",
            (cart_item_id,)
        )
        cart_item = cursor.fetchone()

        if not cart_item:
            return jsonify({"message": "Cart item not found"}), 404
        if cart_item['status'] != 'ordered':
            return jsonify({"message": f"Cannot decline order. Current status: {cart_item['status']}"}), 400

        trade_id = cart_item['trade_id']

        # 2. Verify seller ownership of the associated trade
        cursor.execute(
            "SELECT user_id FROM trades WHERE id = %s",
            (trade_id,)
        )
        trade = cursor.fetchone()
        if not trade:
            # Trade might have been deleted, error out.
            return jsonify({"message": "Associated trade {trade_id} not found"}), 404

        if trade['user_id'] != seller_id:
            return jsonify({"message": "You are not the seller for this item"}), 403

        # --- Perform Updates within a Transaction ---

        # 3. Update cart item status to 'cancelled'
        cursor.execute(
            "UPDATE cart_items SET status = 'cancelled' WHERE id = %s",
            (cart_item_id,)
        )
        if cursor.rowcount == 0:
             raise psycopg2.Error("Failed to update cart item status to cancelled")

        # 4. Increment seller's cancelled count
        cursor.execute(
            "UPDATE users SET count_cancelled = count_cancelled + 1 WHERE id = %s",
            (seller_id,)
        )
        if cursor.rowcount == 0:
             raise psycopg2.Error("Failed to update seller cancellation count")

        # If updates successful, commit the transaction
        conn.commit()
        print(f"Order declined (cart_item {cart_item_id}) by seller {seller_id}. Transaction committed.")
        return jsonify({"message": "Order declined successfully"}), 200

    # Catch PostgreSQL Errors
    except psycopg2.Error as db_e:
        if conn:
            conn.rollback() # Rollback transaction on error
        print(f"Database error during order decline process for cart_item {cart_item_id}: {db_e}")
        return jsonify({"message": "Database error during order decline"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Unexpected error declining order: {e}")
        return jsonify({"message": "An unexpected error occurred"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

@app.route('/api/seller/orders/<int:cart_item_id>/refuse_payment', methods=['POST'])
@token_required
def seller_refuse_payment(cart_item_id):
    seller_id = g.current_user['id']

    conn = None
    cursor = None
    try:
        conn = get_db()
        # Use DictCursor for initial checks
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # --- Initial Checks ---
        # 1. Fetch cart item and verify status
        cursor.execute(
            "SELECT user_id, trade_id, status FROM cart_items WHERE id = %s",
            (cart_item_id,)
        )
        cart_item = cursor.fetchone()

        if not cart_item:
            return jsonify({"message": "Cart item not found"}), 404
        if cart_item['status'] != 'payment_confirmed':
            return jsonify({"message": f"Cannot refuse payment. Current status: {cart_item['status']}"}), 400

        trade_id = cart_item['trade_id']

        # 2. Verify seller ownership of the associated trade
        cursor.execute(
            "SELECT user_id FROM trades WHERE id = %s",
            (trade_id,)
        )
        trade = cursor.fetchone()
        if not trade:
            # Trade might have been deleted, error out.
            return jsonify({"message": "Associated trade {trade_id} not found"}), 404

        if trade['user_id'] != seller_id:
            return jsonify({"message": "You are not the seller for this item"}), 403

        # --- Perform Updates within a Transaction ---

        # 3. Update cart item status to 'cancelled'
        cursor.execute(
            "UPDATE cart_items SET status = 'cancelled' WHERE id = %s",
            (cart_item_id,)
        )
        if cursor.rowcount == 0:
             raise psycopg2.Error("Failed to update cart item status to cancelled")

        

        # If updates successful, commit the transaction
        conn.commit()
        print(f"Payment refused (cart_item {cart_item_id}) by seller {seller_id}. Transaction committed.")
        return jsonify({"message": "Payment refused successfully"}), 200

    # Catch PostgreSQL Errors
    except psycopg2.Error as db_e:
        if conn:
            conn.rollback() # Rollback transaction on error
        print(f"Database error during payment refuse process for cart_item {cart_item_id}: {db_e}")
        return jsonify({"message": "Database error during payment refuse"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Unexpected error refusing payment: {e}")
        return jsonify({"message": "An unexpected error occurred"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

# --- Contact Form Submission Route (Modified) ---
@app.route('/api/contact', methods=['POST'])
@token_required # Keep protected
def handle_contact_form():
    """Handles submission from the contact form, saving to PostgreSQL."""
    data = request.get_json()

    if not data or not data.get('name') or not data.get('email') or not data.get('message'):
        return jsonify({"message": "Missing required fields (name, email, message)"}), 400

    name = data['name']
    email = data['email']
    subject = data.get('subject', '') # Subject is optional
    message = data['message']

    # Basic email format check (keep existing)
    if '@' not in email or '.' not in email.split('@')[-1]:
         return jsonify({"message": "Invalid email format"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Use %s placeholders and RETURNING id
        cursor.execute(
            """INSERT INTO contacts (name, email, subject, message)
               VALUES (%s, %s, %s, %s)
               RETURNING id""",
            (name, email, subject, message)
        )
        # Fetch the returned id
        contact_id_row = cursor.fetchone()
        if contact_id_row is None:
            raise Exception("Contact message saving failed, could not retrieve new ID.")
        contact_id = contact_id_row[0]

        conn.commit()
        print(f"Contact message received successfully with ID: {contact_id}")

        return jsonify({"message": "Contact message received successfully.", "contactId": contact_id}), 201

    # Catch PostgreSQL errors
    except (Exception, psycopg2.DatabaseError) as e:
        if conn:
            conn.rollback()
        print(f"Database error saving contact message: {e}")
        return jsonify({"message": "Database error saving message"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

# --- Function to export contacts to CSV (Refactored for Download) ---
def export_contacts_to_csv_string():
    """Fetches all contacts from contacts table and returns them as a CSV string."""
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor() # Standard cursor is fine
        cursor.execute("SELECT id, name, email, subject, message, submitted_at FROM contacts ORDER BY submitted_at ASC")
        contacts = cursor.fetchall()

        # Use StringIO to create CSV in memory
        si = StringIO()
        cw = csv.writer(si)

        # Write Header
        if cursor.description:
            column_names = [desc[0] for desc in cursor.description]
            cw.writerow(column_names)
        else: # Handle case with no contacts/columns
            cw.writerow(['id', 'name', 'email', 'subject', 'message', 'submitted_at']) # Default header

        # Write Data Rows
        if contacts:
            cw.writerows(contacts)

        output = si.getvalue()
        si.close()
        print(f"Generated CSV string for {len(contacts)} contacts.")
        return output

    # Catch PostgreSQL errors
    except psycopg2.Error as e:
        print(f"Database error during contact CSV generation: {e}")
        raise # Re-raise the error to be handled by the route
    except Exception as e:
        print(f"General error during contact CSV generation: {e}")
        raise # Re-raise the error
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

# --- New route for downloading contacts CSV ---
@app.route('/api/contacts/export', methods=['GET'])
@token_required # Protect this route (add admin role check later if needed)
def download_contacts_export():
    """Provides contact form submissions as a downloadable CSV file."""
    try:
        csv_data = export_contacts_to_csv_string() # Call the refactored function
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition":
                     "attachment; filename=contact_submissions.csv"}
        )
    except Exception as e:
        # Error messages already printed in export_contacts_to_csv_string
        return jsonify({"message": "Failed to generate contact export"}), 500

# --- New endpoint to UPDATE user payment info --- 
@app.route('/api/profile/payment', methods=['PUT'])
@token_required
def update_payment_info():
    """Updates the payment information for the logged-in user."""
    user_id = g.current_user['id']
    data = request.get_json()

    if not data:
        return jsonify({"message": "No update data provided"}), 400

    # Fields allowed for update
    allowed_fields = ['bank_name', 'bank_account_number', 'bank_account_name']
    fields_to_update = {}
    
    # Validate and collect provided fields
    for field in allowed_fields:
        if field in data:
            # Basic validation: Treat empty strings as NULL/None perhaps?
            # Or enforce non-empty if needed.
            # For now, just accept the string value provided.
            value = data[field]
            if isinstance(value, str):
                fields_to_update[field] = value.strip() if value.strip() else None
            else:
                 fields_to_update[field] = None # Set to null if not a string

    if not fields_to_update: # Check if any valid fields were provided
        return jsonify({"message": "No valid payment fields provided for update"}), 400

    # Construct the SET clause and parameter list using %s
    set_clause = ", ".join([f"{field} = %s" for field in fields_to_update])
    params = list(fields_to_update.values())
    params.append(user_id) # Add user_id for the WHERE clause

    sql = f"UPDATE users SET {set_clause} WHERE id = %s RETURNING id, fullname, email, bank_name, bank_account_number, bank_account_name"

    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(sql, tuple(params))

        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({"message": "User update failed (user not found?)"}), 500
        
        updated_user_info = cursor.fetchone()
        conn.commit()
        
        print(f"Payment info updated successfully for user {user_id}.")
        return jsonify({
            "message": "Payment information updated successfully",
            # Return the updated fields
            "payment_info": dict(updated_user_info) if updated_user_info else None 
        }), 200

    except psycopg2.Error as e:
        if conn: conn.rollback()
        print(f"Database error updating payment info for user {user_id}: {e}")
        return jsonify({"message": "Database error updating payment information"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error updating payment info for user {user_id}: {e}")
        return jsonify({"message": "An unexpected error occurred"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

# --- New endpoint to get full user profile data ---
@app.route('/api/profile', methods=['GET'])
@token_required
def get_user_profile():
    """Returns the full profile data for the logged-in user."""
    # The token_required decorator has already fetched the user data including payment info
    # and stored it in g.current_user
    if not hasattr(g, 'current_user') or not g.current_user:
        return jsonify({"message": "Failed to retrieve user data from context"}), 500
    
    # Convert DictRow to a regular dictionary for JSON serialization
    user_data = dict(g.current_user)
    
    # We might want to exclude the password hash if it was somehow included
    # (Although the current query in token_required doesn't fetch it)
    user_data.pop('password', None) 

    return jsonify({"user_profile": user_data}), 200

# --- New endpoint for buyer to confirm payment --- 
@app.route('/api/cart/items/<int:cart_item_id>/confirm-payment', methods=['POST'])
@token_required
def buyer_confirm_payment(cart_item_id):
    buyer_id = g.current_user['id']
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Check if cart item exists, belongs to the user, and is in 'accepted' status
        cursor.execute(
            "SELECT id, user_id, trade_id, status FROM cart_items WHERE id = %s", 
            (cart_item_id,)
        )
        cart_item = cursor.fetchone()

        if not cart_item:
            return jsonify({"message": "Order item not found"}), 404
        if cart_item['user_id'] != buyer_id:
            return jsonify({"message": "Not authorized to update this item"}), 403
        if cart_item['status'] != 'accepted':
            return jsonify({"message": f"Order cannot be marked as paid. Current status: {cart_item['status']}"}), 400

        # Update status to 'payment_confirmed'
        cursor.execute(
            "UPDATE cart_items SET status = 'payment_confirmed' WHERE id = %s",
            (cart_item_id,)
        )

        if cursor.rowcount == 0:
            raise psycopg2.Error("Failed to update cart item status to payment_confirmed")

        conn.commit()
        print(f"Payment confirmed by buyer {buyer_id} for cart item {cart_item_id}")
        return jsonify({"message": "Payment confirmed successfully. Awaiting seller completion."}), 200

    except psycopg2.Error as e:
        if conn: conn.rollback()
        print(f"DB Error confirming payment for {cart_item_id}: {e}")
        return jsonify({"message": "Database error confirming payment"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error confirming payment for {cart_item_id}: {e}")
        return jsonify({"message": "An error occurred"}), 500
    finally:
        if cursor is not None:
            cursor.close()

# --- New endpoint for seller to complete an order --- 
@app.route('/api/seller/orders/<int:cart_item_id>/complete', methods=['POST'])
@token_required
def seller_complete_payment(cart_item_id):
    seller_id = g.current_user['id']
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Fetch cart item and associated trade to verify seller and status
        cursor.execute(
            """SELECT ci.id, ci.status, ci.trade_id, ci.quantity, t.user_id AS seller_user_id
               FROM cart_items ci
               JOIN trades t ON ci.trade_id = t.id
               WHERE ci.id = %s""",
            (cart_item_id,)
        )
        order_info = cursor.fetchone()

        if not order_info:
            return jsonify({"message": "Order item not found"}), 404
        if order_info['seller_user_id'] != seller_id:
            return jsonify({"message": "You are not the seller for this item"}), 403
        if order_info['status'] != 'payment_confirmed':
            return jsonify({"message": f"Cannot complete payment. Status must be 'payment_confirmed'. Current: {order_info['status']}"}), 400

        # Extract needed info for stock update
        trade_id = order_info['trade_id']
        ordered_quantity = order_info['quantity']

        # --- Start Transaction ---
        # 2. Update cart item status to 'completed'
        cursor.execute(
            "UPDATE cart_items SET status = 'completed' WHERE id = %s",
            (cart_item_id,)
        )
        if cursor.rowcount == 0:
            raise psycopg2.Error("Failed to update cart item status to completed")

        # 3. Increment seller's completed count
        cursor.execute(
            "UPDATE users SET count_completed = count_completed + 1 WHERE id = %s",
            (seller_id,)
        )
        if cursor.rowcount == 0:
            raise psycopg2.Error("Failed to update seller completion count")

        # 4. Decrement stock in trade DB
        cursor.execute(
            "UPDATE trades SET quantity = quantity - %s WHERE id = %s",
            (ordered_quantity, trade_id)
        )
        if cursor.rowcount == 0:
            # This implies the trade was deleted between fetching order_info and this update, which is unlikely but possible.
            raise psycopg2.Error(f"Failed to decrement stock for trade {trade_id} (rowcount 0). Trade might have been deleted.")
        
        # --- Commit Transaction ---
        conn.commit()

        print(f"Order {cart_item_id} marked as completed by seller {seller_id}")
        return jsonify({"message": "Payment completed successfully!"}), 200

    except psycopg2.Error as e:
        if conn: conn.rollback()
        print(f"DB Error completing payment {cart_item_id}: {e}")
        return jsonify({"message": "Database error completing payment"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error completing payment: {e}")
        return jsonify({"message": "An unexpected error occurred"}), 500
    finally:
        if cursor is not None:
            cursor.close()
        # Connection closed by teardown context
        pass

# --- New endpoint to get seller payment info for QR code --- 
@app.route('/api/cart/items/<int:cart_item_id>/seller-payment-info', methods=['GET']) # MODIFIED: Route uses cart_item_id
@token_required # Buyer needs to be logged in to request this
def get_seller_payment_info(cart_item_id): # MODIFIED: Parameter is cart_item_id
    """Gets seller payment info based on a specific cart item ID.
       Verifies the requester is the buyer for this cart item.
    """
    buyer_id = g.current_user['id'] # Get logged-in user ID
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # MODIFIED: Fetch cart item first to get trade_id and verify buyer
        cursor.execute(
            "SELECT user_id, trade_id FROM cart_items WHERE id = %s", 
            (cart_item_id,)
        )
        cart_item = cursor.fetchone()

        if not cart_item:
            return jsonify({"message": "Order item not found"}), 404
        
        # MODIFIED: Verify the requester is the buyer
        if cart_item['user_id'] != buyer_id:
            return jsonify({"message": "Not authorized to view payment info for this order"}), 403
            
        trade_id = cart_item['trade_id'] # Get trade_id from cart item

        # Fetch seller ID from trade (using the retrieved trade_id)
        cursor.execute("SELECT user_id FROM trades WHERE id = %s", (trade_id,))
        trade = cursor.fetchone()
        if not trade:
            # This could happen if the trade was deleted after the cart item was created
            return jsonify({"message": f"Associated trade (ID: {trade_id}) not found"}), 404 
        seller_id = trade['user_id']

        # Fetch seller payment details from users table
        cursor.execute(
            "SELECT bank_name, bank_account_number, bank_account_name FROM users WHERE id = %s",
            (seller_id,)
        )
        seller_info = cursor.fetchone()

        if not seller_info:
            # Should not happen if trade exists, but good to check
            return jsonify({"message": "Seller information not found"}), 404
            
        # Check if seller has provided necessary info
        bank_name = seller_info['bank_name']
        account_no = seller_info['bank_account_number']
        account_name = seller_info['bank_account_name']

        if not bank_name or not account_no: # Account name is optional for VietQR link but good to have
             return jsonify({"message": "Seller has not provided complete payment information (Bank Name and Account Number required)."}), 404 # 404 or maybe 400?

        # Map bank name to VietQR Bank ID
        bank_id = VIETQR_BANK_MAP.get(bank_name)
        if not bank_id:
            print(f"Warning: Bank name '{bank_name}' not found in VIETQR_BANK_MAP for seller {seller_id}")
            # Return a specific error or try to proceed without BANK_ID? VietQR needs it.
            return jsonify({"message": f"Payment setup error: Bank '{bank_name}' is not supported for QR generation."}), 400
            
        # Return the necessary info
        return jsonify({
            "bank_id": bank_id,
            "account_number": account_no,
            "account_name": account_name or "" # Return empty string if None
        }), 200

    except psycopg2.Error as e:
        print(f"DB Error getting seller payment info for trade {trade_id}: {e}")
        return jsonify({"message": "Database error retrieving seller payment info"}), 500
    except Exception as e:
        print(f"Error getting seller payment info for trade {trade_id}: {e}")
        return jsonify({"message": "An error occurred retrieving seller payment info"}), 500
    finally:
        if cursor is not None:
            cursor.close()

# --- Main execution block ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)