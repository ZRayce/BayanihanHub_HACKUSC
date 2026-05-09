import os
import threading
import sqlite3
import random
import json
import smtplib
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

app = Flask(__name__, template_folder='templates', static_folder='static')

# --- CONFIGURATION (Render Friendly) ---
app.secret_key = os.environ.get('SECRET_KEY', 'bayanihan_hub_secret_key_2026')
GMAIL_USER = os.environ.get('MAIL_USERNAME', 'noreply.bayanihanhub@gmail.com') 
GMAIL_PASS = os.environ.get('MAIL_PASSWORD', 'fjom yntw wsca nlhf')       

# --- DATABASE SETUP ---
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Users Table
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
    # OTP Requests Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS otp_requests (
            phone_number TEXT PRIMARY KEY,
            otp_code TEXT NOT NULL,
            temp_data TEXT NOT NULL
        )
    ''')
    # Reports Table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            image_path TEXT,
            status TEXT DEFAULT 'Pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # --- ROOT ADMIN SETUP ---
    ADMIN_EMAIL = 'admin.bayanihanhub@cebu.gov.ph' 
    ADMIN_PASS = 'Bayanihan_Secure_2026!' 
    ADMIN_PHONE = '0000'

    admin = conn.execute("SELECT * FROM users WHERE role = 'official'").fetchone()
    hashed_pw = generate_password_hash(ADMIN_PASS)
    
    if not admin:
        try:
            conn.execute('''
                INSERT INTO users (full_name, email, phone_number, password_hash, role) 
                VALUES ('Brgy Command Center', ?, ?, ?, 'official')
            ''', (ADMIN_EMAIL, ADMIN_PHONE, hashed_pw))
            conn.commit()
            print(f"⭐ [SYSTEM] Root Admin Created: {ADMIN_EMAIL}")
        except sqlite3.IntegrityError:
            pass
    else:
        conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (hashed_pw, ADMIN_EMAIL))
        conn.commit()
    
    conn.close()

init_db()

# --- LOGIN PROTECTION ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- PRODUCTION EMAIL SENDER ---
def send_email_otp(receiver_email, otp):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Verification Code: {otp}'
        msg['From'] = f'"BayanihanHub Official" <{GMAIL_USER}>'
        msg['To'] = receiver_email
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
            <div style="max-width: 500px; margin: auto; background: white; border-radius: 24px; border: 1px solid #e2e8f0; overflow: hidden;">
              <div style="background-color: #6d28d9; padding: 30px; text-align: center;"><h1 style="color: white; margin: 0;">BayanihanHub</h1></div>
              <div style="padding: 40px; text-align: center;">
                <h2 style="color: #1e293b;">Maayong adlaw!</h2>
                <p style="color: #64748b;">Gamita kini nga code para ma-verify ang imong account:</p>
                <div style="background-color: #f1f5f9; padding: 20px; border-radius: 16px; margin: 24px 0; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #6d28d9; border: 1px dashed #cbd5e1;">{otp}</div>
                <p style="font-size: 12px; color: #94a3b8;">If you didn't request this, please ignore this email.</p>
              </div>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        
        # SSL Port 465 is more reliable on Render/Cloud environments
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ SMTP Error Detail: {e}")
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

    # --- HACKATHON BACKUP LOGGING (Check Render logs for this!) ---
    print(f"\n🚀 [DEMO LOG] OTP FOR {email}: {otp_code}\n")

    try:
        conn = get_db_connection()
        conn.execute('INSERT OR REPLACE INTO otp_requests (phone_number, otp_code, temp_data) VALUES (?, ?, ?)',
                     (phone, otp_code, json.dumps(data)))
        conn.commit()
        conn.close()

        # Background Threading for Email
        def run_email_in_thread(app_instance, target_email, code):
            with app_instance.app_context():
                success = send_email_otp(target_email, code)
                if success:
                    print(f"✅ EMAIL SENT to {target_email}")
                else:
                    print(f"⚠️ EMAIL FAILED. Use backup code: {code}")

        threading.Thread(target=run_email_in_thread, args=(app._get_current_object(), email, otp_code)).start()

        return jsonify({"message": "OTP generated! Check your email."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    phone = data.get('phone')
    user_code = data.get('code')
    
    # 🔥 HACKATHON MASTER BYPASS (LIFESAVER!)
    # Logic: If 123456 is used, it attempts to register the user from the last temp_data
    is_bypass = (user_code == '123456')

    conn = get_db_connection()
    record = conn.execute('SELECT * FROM otp_requests WHERE phone_number = ?', (phone,)).fetchone()
    
    if record and (record['otp_code'] == user_code or is_bypass):
        user_details = json.loads(record['temp_data'])
        hashed_pw = generate_password_hash(user_details['password'])
        try:
            # Register the user
            conn.execute('INSERT OR IGNORE INTO users (full_name, email, phone_number, password_hash, role) VALUES (?, ?, ?, ?, "citizen")',
                         (user_details['name'], user_details['email'], phone, hashed_pw))
            
            # Clean up the OTP request
            conn.execute('DELETE FROM otp_requests WHERE phone_number = ?', (phone,))
            conn.commit()
            
            # Auto-login after registration
            user = conn.execute('SELECT user_id, role FROM users WHERE phone_number = ?', (phone,)).fetchone()
            session['user_id'] = user['user_id']
            session['role'] = user['role']
            
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

# --- BLUEPRINTS ---
from user import user_bp
app.register_blueprint(user_bp)

# --- UTILITY ROUTES ---
@app.route('/api/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if session.get('role') != 'official':
        return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('Admin_Dashboard.html', user=user)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
