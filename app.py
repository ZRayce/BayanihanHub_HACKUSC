import threading
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import email
import sqlite3
import random
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

app = Flask(__name__, template_folder='templates', static_folder='static')

# --- CONFIGURATION ---
app.secret_key = 'bayanihan_hub_secret_key_2026'
GMAIL_USER = 'noreply.bayanihanhub@gmail.com' 
GMAIL_PASS = 'fjom yntw wsca nlhf'       

# --- DATABASE SETUP ---
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # 1. Create Tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone_number TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            hero_points INTEGER DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS otp_requests (
            phone_number TEXT PRIMARY KEY,
            otp_code TEXT NOT NULL,
            temp_data TEXT NOT NULL
        )
    ''')

    # 3. Create Reports Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # --- ROOT ADMIN SETUP ---
    ADMIN_EMAIL = 'admin.bayanihanhub@cebu.gov.ph' 
    ADMIN_PASS = 'Bayanihan_Secure_2026!' 
    ADMIN_PHONE = '0000' # Admin default phone

    # Check if admin already exists by role to avoid IntegrityError
    admin = conn.execute("SELECT * FROM users WHERE role = 'official'").fetchone()
    
    if not admin:
        hashed_pw = generate_password_hash(ADMIN_PASS)
        try:
            conn.execute('''
                INSERT INTO users (full_name, email, phone_number, password_hash, role) 
                VALUES ('Brgy Command Center', ?, ?, ?, 'official')
            ''', (ADMIN_EMAIL, ADMIN_PHONE, hashed_pw))
            conn.commit()
            print(f"⭐ [SYSTEM] Root Admin Created: {ADMIN_EMAIL}")
        except sqlite3.IntegrityError:
            print("⚠️ [SYSTEM] Integrity Check: Admin already in database.")
    else:
        # Piliting i-update ang password tuwing mag-re-restart ang server
        hashed_pw = generate_password_hash(ADMIN_PASS)
        conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (hashed_pw, ADMIN_EMAIL))
        conn.commit()
        print(f"✅ [SYSTEM] Admin Account Ready & Password Force-Updated: {admin['email']}")
    
    conn.close()

# Run database initialization
init_db()

# --- LOGIN PROTECTION DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- EMAIL SENDER FUNCTION ---
def send_email_otp(receiver_email, otp):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Verification Code: {otp}'
        msg['From'] = f'"BayanihanHub Official" <{GMAIL_USER}>'
        msg['To'] = receiver_email
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #0f172a; background-color: #f8fafc; padding: 20px;">
            <div style="max-width: 500px; margin: auto; background: white; border-radius: 24px; overflow: hidden; border: 1px solid #e2e8f0;">
              <div style="background-color: #1d4ed8; padding: 30px; text-align: center;"><h1 style="color: white; margin: 0; font-size: 24px;">BayanihanHub</h1></div>
              <div style="padding: 40px; text-align: center;">
                <h2 style="font-size: 20px; margin-bottom: 8px;">Maayong adlaw!</h2>
                <p style="color: #64748b; font-size: 14px;">Gamita kini nga code para ma-verify ang imong account.</p>
                <div style="background-color: #f1f5f9; padding: 20px; border-radius: 16px; margin: 24px 0; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #1d4ed8; border: 1px dashed #cbd5e1;">{otp}</div>
              </div>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('BayanihanHub_LandingPAGE.html')

@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    phone = data.get('phone')
    
    if email == 'admin.bayanihanhub@cebu.gov.ph':
        return jsonify({"error": "Reserved email. Official use only."}), 400
    
    otp_code = str(random.randint(100000, 999999))

    # --- DEBUG PRINT (DITO MO MAKIKITA ANG CODE SA TERMINAL) ---
    print("\n" + "="*40)
    print(f"🚀 [BACKUP] OTP FOR {email} IS: {otp_code}")
    print("="*40 + "\n")
    # ---------------------------------------------------------

    try:
        conn = get_db_connection()
        conn.execute('INSERT OR REPLACE INTO otp_requests (phone_number, otp_code, temp_data) VALUES (?, ?, ?)',
                     (phone, otp_code, json.dumps(data)))
        conn.commit()
        conn.close()

        # ─── MABILIS NA EMAIL SENDER (WITH FLASK CONTEXT) ───
        from flask import current_app
        app_ctx = current_app.app_context()

        def run_email_in_thread(ctx, target_email, code):
            with ctx:
                try:
                    send_email_otp(target_email, code)
                    print(f"✅ SUCCESS: OTP sent to {target_email} in background!")
                except Exception as e:
                    print(f"❌ ERROR: Failed to send OTP email: {e}")

        email_thread = threading.Thread(target=run_email_in_thread, args=(app_ctx, email, otp_code))
        email_thread.start() 

        return jsonify({"message": "OTP generated! Check email or terminal."}), 200

    except Exception as e:
        return jsonify({"error": "Failed to process request."}), 500
            
@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    phone = data.get('phone')
    user_code = data.get('code')
    
    conn = get_db_connection()
    record = conn.execute('SELECT * FROM otp_requests WHERE phone_number = ?', (phone,)).fetchone()
    
    if record and record['otp_code'] == user_code:
        user_details = json.loads(record['temp_data'])
        hashed_pw = generate_password_hash(user_details['password'])
        try:
            conn.execute('INSERT INTO users (full_name, email, phone_number, password_hash, role) VALUES (?, ?, ?, ?, "citizen")',
                         (user_details['name'], user_details['email'], phone, hashed_pw))
            conn.execute('DELETE FROM otp_requests WHERE phone_number = ?', (phone,))
            conn.commit()
            conn.close()
            return jsonify({"message": "Success", "redirect_url": "/user-dashboard"}), 200
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"error": "User already exists"}), 400
    conn.close()
    return jsonify({"error": "Invalid code"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['user_id']
        session['role'] = user['role']
        url = '/admin-dashboard' if user['role'] == 'official' else '/user-dashboard'
        return jsonify({"message": "Login Success", "redirect_url": url}), 200
    
    return jsonify({"error": "Incorrect email or password."}), 401

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
    # Security check: Does the email exist?
    if not user:
        conn.close()
        return jsonify({"error": "Hindi namin mahanap ang email na ito."}), 404
            
    otp_code = str(random.randint(100000, 999999))
        
    # --- DEBUG PRINT PARA SA TERMINAL ---
    print("\n" + "="*40)
    print(f"🔑 [PASSWORD RESET] OTP FOR {email}: {otp_code}")
    print("="*40 + "\n")
    
    try:
        conn.execute('INSERT OR REPLACE INTO otp_requests (phone_number, otp_code, temp_data) VALUES (?, ?, ?)',
                     (email, otp_code, 'reset_password'))
        conn.commit()
        conn.close()
            
        # ─── MABILIS NA EMAIL SENDER (WITH FLASK CONTEXT) ───
        from flask import current_app
        app_ctx = current_app.app_context()

        def run_email_in_thread(ctx, target_email, code):
            with ctx:
                try:
                    send_email_otp(target_email, code)
                    print(f"✅ SUCCESS: Reset code sent to {target_email} in background!")
                except Exception as e:
                    print(f"❌ ERROR: Failed to send reset email: {e}")

        email_thread = threading.Thread(target=run_email_in_thread, args=(app_ctx, email, otp_code))
        email_thread.start() 

        return jsonify({"message": "Reset code sent!"}), 200
    
    except Exception as e:
        return jsonify({"error": "Failed to generate reset code."}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    code = data.get('code')
    new_password = data.get('new_password')
        
    conn = get_db_connection()
    record = conn.execute('SELECT * FROM otp_requests WHERE phone_number = ?', (email,)).fetchone()
        
    # Verify the OTP code
    if record and record['otp_code'] == code and record['temp_data'] == 'reset_password':
        hashed_pw = generate_password_hash(new_password)
        # Update password
        conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (hashed_pw, email))
        # Clean up OTP
        conn.execute('DELETE FROM otp_requests WHERE phone_number = ?', (email,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Password updated successfully!"}), 200
        
    conn.close()
    return jsonify({"error": "Invalid or expired code."}), 400

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# --- DASHBOARDS ---

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('Admin_Dashboard.html', user=user)

# --- ERROR HANDLERS ---

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# --- REGISTER BLUEPRINTS ---
from user import user_bp
app.register_blueprint(user_bp)

# --- ERROR HANDLERS ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)