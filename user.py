from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import sqlite3
import os
import base64
import uuid

# Gumagawa tayo ng 'Blueprint' na tatawagin nating 'user'
user_bp = Blueprint('user', __name__)

# --- UTILS FOR USER ROUTES ---
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

# --- USER ROUTES ---

@user_bp.route('/user-dashboard')
@login_required
def user_dashboard():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('User_Dashboard.html', user=user)

@user_bp.route('/api/submit-report', methods=['POST'])
@login_required
def submit_report():
    data = request.json
    category = data.get('category')
    location = data.get('location')
    description = data.get('description')
    image_data = data.get('image') # Base64 string from frontend
    user_id = session['user_id']
    
    image_path = None

    # Logic para i-save ang ebidensya (Photo)
    if image_data:
        try:
            # Create uploads folder if not exists
            if not os.path.exists('static/uploads'):
                os.makedirs('static/uploads')
                
            header, encoded = image_data.split(',', 1)
            file_ext = header.split('/')[1].split(';')[0]
            filename = f"report_{uuid.uuid4().hex}.{file_ext}"
            filepath = os.path.join('static', 'uploads', filename)
            
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(encoded))
            
            image_path = f"/static/uploads/{filename}"
        except Exception as e:
            print(f"Image Save Error: {e}")

    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO reports (user_id, category, location, description, image_path) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, category, location, description, image_path))
        
        # Dagdag 10 points kay user
        conn.execute('UPDATE users SET hero_points = hero_points + 10 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Report submitted! You earned 10 Hero Points! 🌟"}), 200
    except Exception as e:
        print(f"Database Error: {e}")
        return jsonify({"error": "Failed to submit report."}), 500

@user_bp.route('/api/get-reports', methods=['GET'])
def get_reports():
    """Kinukuha ang reports para sa User Dashboard at Admin Command Center"""
    try:
        conn = get_db_connection()
        # JOIN users para makuha ang pangalan at points ng nag-report (Importante sa Admin side)
        reports = conn.execute('''
            SELECT reports.*, users.full_name, users.hero_points 
            FROM reports 
            JOIN users ON reports.user_id = users.user_id 
            ORDER BY timestamp DESC
        ''').fetchall()
        conn.close()
        return jsonify([dict(r) for r in reports]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@user_bp.route('/api/redeem', methods=['POST'])
@login_required
def redeem_item():
    data = request.json
    cost = data.get('cost')
    item_name = data.get('item_name')
    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT hero_points FROM users WHERE user_id = ?', (user_id,)).fetchone()
        
        if user['hero_points'] >= cost:
            conn.execute('UPDATE users SET hero_points = hero_points - ? WHERE user_id = ?', (cost, user_id))
            conn.commit()
            conn.close()
            return jsonify({"message": f"Successfully redeemed {item_name}! Please claim at the Barangay Hall."}), 200
        else:
            conn.close()
            return jsonify({"error": "Not enough Hero Points!"}), 400
    except Exception as e:
        return jsonify({"error": "Failed to process redemption."}), 500