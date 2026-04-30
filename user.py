from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import sqlite3

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
    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO reports (user_id, category, location, description) VALUES (?, ?, ?, ?)',
                     (user_id, category, location, description))
        conn.execute('UPDATE users SET hero_points = hero_points + 10 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Report submitted! You earned 10 Hero Points! 🌟"}), 200
    except Exception as e:
        print(f"Report Error: {e}")
        return jsonify({"error": "Failed to submit report."}), 500

@user_bp.route('/api/get-reports', methods=['GET'])
@login_required
def get_reports():
    try:
        conn = get_db_connection()
        reports = conn.execute('SELECT * FROM reports ORDER BY timestamp DESC').fetchall()
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
            return jsonify({"error": "Not enough Hero Points! Keep reporting to earn more."}), 400
    except Exception as e:
        return jsonify({"error": "Failed to process redemption."}), 500