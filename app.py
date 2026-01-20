import os
import sqlite3
import qrcode
from flask import Flask, request, render_template, redirect, url_for, send_file, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super-secret-admin-key"

UPLOAD_FOLDER = "uploads"
QR_FOLDER = "qr_codes"
DATABASE = "database.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

# ---------- DATABASE SETUP ----------

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            unique_code TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            month TEXT,
            filename TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- ADMIN LOGIN ----------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == "admin" and request.form['password'] == "admin123":
            session['admin'] = True
            return redirect(url_for('dashboard'))
        return "Invalid login"
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

# ---------- DASHBOARD (ADMIN ONLY) ----------

@app.route('/')
@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM customers")
    customers = c.fetchall()
    conn.close()

    return render_template("index.html", customers=customers)

# ---------- CREATE CUSTOMER ----------

@app.route('/create_customer', methods=['POST'])
def create_customer():
    if not session.get('admin'):
        return redirect(url_for('login'))

    name = request.form['name']
    unique_code = f"CUST{int(datetime.now().timestamp())}"

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO customers (name, unique_code) VALUES (?, ?)", (name, unique_code))
    conn.commit()
    customer_id = c.lastrowid
    conn.close()

    generate_qr(unique_code)
    return redirect(url_for('dashboard'))

# ---------- GENERATE QR ----------

def generate_qr(unique_code):
    BASE_URL = "https://video-upload-qr-app.onrender.com"
    upload_url = f"{BASE_URL}/upload/{unique_code}"

    img = qrcode.make(upload_url)
    img.save(os.path.join(QR_FOLDER, f"{unique_code}.png"))

@app.route('/download_qr/<unique_code>')
def download_qr(unique_code):
    return send_file(os.path.join(QR_FOLDER, f"{unique_code}.png"), as_attachment=True)

# ---------- DELETE CUSTOMER ----------

@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM uploads WHERE customer_id = ?", (customer_id,))
    c.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

# ---------- VIDEO UPLOAD (QR USERS ONLY) ----------

@app.route('/upload/<unique_code>', methods=['GET', 'POST'])
def upload(unique_code):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT id FROM customers WHERE unique_code = ?", (unique_code,))
    result = c.fetchone()

    if not result:
        return "Invalid QR Code"

    customer_id = result[0]
    current_month = datetime.now().strftime("%Y-%m")

    if request.method == 'POST':
        file = request.files['video']

        c.execute("SELECT * FROM uploads WHERE customer_id=? AND month=?",
                  (customer_id, current_month))

        if c.fetchone():
            return "You have already uploaded this month."

        filename = f"{unique_code}_{current_month}_{file.filename}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        c.execute("INSERT INTO uploads (customer_id, month, filename) VALUES (?, ?, ?)",
                  (customer_id, current_month, filename))

        conn.commit()
        conn.close()
        return render_template("success.html")

    conn.close()
    return render_template("upload.html")

# ---------- MONTHLY REPORT (ADMIN ONLY) ----------

@app.route('/report')
def report():
    if not session.get('admin'):
        return redirect(url_for('login'))

    year = request.args.get('year')
    month = request.args.get('month')

    if not year or not month:
        now = datetime.now()
        year, month = now.strftime("%Y"), now.strftime("%m")

    selected_month = f"{year}-{month}"
    current_month = datetime.now().strftime("%Y-%m")

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, name, unique_code FROM customers")
    customers = c.fetchall()

    report_data = []

    for cid, name, code in customers:
        c.execute("SELECT * FROM uploads WHERE customer_id=? AND month=?",
                  (cid, selected_month))
        upload = c.fetchone()

        if upload:
            status = "SUBMITTED"
        elif selected_month < current_month:
            status = "NOT SUBMITTED"
        else:
            status = "PENDING"

        report_data.append((name, code, status))

    conn.close()

    return render_template(
        "report.html",
        data=report_data,
        selected_year=year,
        selected_month=month
    )

# ---------- RUN ----------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
