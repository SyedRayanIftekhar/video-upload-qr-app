import os
import sqlite3
import qrcode
from flask import Flask, request, render_template, redirect, url_for, send_file
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
QR_FOLDER = "qr_codes"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

DATABASE = "database.db"


# ---------- DATABASE SETUP ----------

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            unique_code TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            month TEXT,
            filename TEXT
        )
    ''')

    conn.commit()
    conn.close()


init_db()


# ---------- HOME PAGE ----------

@app.route('/')
def index():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM customers")
    customers = c.fetchall()
    conn.close()

    return render_template("index.html", customers=customers)


# ---------- CREATE NEW CUSTOMER ----------

@app.route('/create_customer', methods=['POST'])
def create_customer():
    name = request.form['name']
    unique_code = f"CUST{int(datetime.now().timestamp())}"

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO customers (name, unique_code) VALUES (?, ?)", (name, unique_code))
    conn.commit()

    customer_id = c.lastrowid
    conn.close()

    generate_qr(customer_id, unique_code)

    return redirect(url_for('index'))


# ---------- GENERATE QR CODE ----------

def generate_qr(customer_id, unique_code):
    upload_url = f"http://127.0.0.1:5000/upload/{unique_code}"

    img = qrcode.make(upload_url)

    qr_path = os.path.join(QR_FOLDER, f"{unique_code}.png")
    img.save(qr_path)


@app.route('/download_qr/<unique_code>')
def download_qr(unique_code):
    path = os.path.join(QR_FOLDER, f"{unique_code}.png")
    return send_file(path, as_attachment=True)


# ---------- VIDEO UPLOAD PAGE ----------

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

        c.execute("""
            SELECT * FROM uploads 
            WHERE customer_id = ? AND month = ?
        """, (customer_id, current_month))

        already_uploaded = c.fetchone()

        if already_uploaded:
            return "You have already uploaded a video this month!"

        filename = f"{unique_code}_{current_month}_{file.filename}"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        c.execute("""
            INSERT INTO uploads (customer_id, month, filename)
            VALUES (?, ?, ?)
        """, (customer_id, current_month, filename))

        conn.commit()
        conn.close()

        return render_template("success.html")

    conn.close()
    return render_template("upload.html")

@app.route('/report', methods=['GET'])
def report():

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    year = request.args.get('year')
    month = request.args.get('month')

    if not year or not month:
        current = datetime.now()
        year = current.strftime("%Y")
        month = current.strftime("%m")

    selected_month = f"{year}-{month}"

    c.execute("SELECT id, name, unique_code FROM customers")
    customers = c.fetchall()

    report_data = []

    # Determine current year-month for comparison
    current_month = datetime.now().strftime("%Y-%m")

    for customer in customers:
        customer_id = customer[0]
        name = customer[1]
        code = customer[2]

        c.execute("""
            SELECT * FROM uploads
            WHERE customer_id = ? AND month = ?
        """, (customer_id, selected_month))

        upload = c.fetchone()

        if upload:
            status = "SUBMITTED"
        else:
            # If selected month is older than current month
            if selected_month < current_month:
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)



