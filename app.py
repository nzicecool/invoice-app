from flask import Flask, jsonify, request
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

DB_PATH = 'invoices.db'

def _db_path():
    return app.config.get('DB_PATH', DB_PATH)

def init_db():
    conn = sqlite3.connect(_db_path(), timeout=10)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            currency TEXT DEFAULT 'AUD',
            items TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax_rate REAL DEFAULT 0.10,
            tax_amount REAL DEFAULT 0.00,
            total REAL NOT NULL,
            status TEXT DEFAULT 'draft',
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_totals(items, tax_rate):
    subtotal = sum(item['qty'] * item['unit_price'] for item in items)
    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount
    return subtotal, tax_amount, total

@app.route('/api/invoices', methods=['POST'])
def create_invoice():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid payload'}), 400

    try:
        invoice_number = data.get('invoice_number', '')
        if not invoice_number:
            return jsonify({'error': 'invoice_number is required'}), 400

        client_name = data.get('client_name', '')
        if not client_name:
            return jsonify({'error': 'client_name is required'}), 400

        issue_date = data.get('issue_date')
        if not issue_date:
            return jsonify({'error': 'issue_date is required'}), 400

        due_date = data.get('due_date')
        if not due_date:
            return jsonify({'error': 'due_date is required'}), 400

        items = data.get('items', [])
        if not items:
            return jsonify({'error': 'items is required'}), 400

        currency = data.get('currency', 'AUD')
        if currency not in ('AUD', 'USD', 'EUR', 'GBP', 'LKR'):
            return jsonify({'error': 'Invalid currency'}), 400
        tax_rate = data.get('tax_rate', 0.10)
        notes = data.get('notes', '')
        status = data.get('status', 'draft')

        subtotal, tax_amount, total = calculate_totals(items, tax_rate)

        created_at = datetime.utcnow().isoformat()
        updated_at = created_at

        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO invoices
            (invoice_number, client_name, client_email, issue_date,
             due_date, currency, items, subtotal, tax_rate,
             tax_amount, total, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_number, client_name, data.get('client_email', ''),
            issue_date, due_date, currency, str(items),
            subtotal, tax_rate, tax_amount, total, status, notes,
            created_at, updated_at
        ))
        invoice_id = c.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'id': invoice_id,
            'invoice_number': invoice_number,
            'client_name': client_name,
            'client_email': data.get('client_email', ''),
            'issue_date': issue_date,
            'due_date': due_date,
            'currency': currency,
            'items': items,
            'subtotal': subtotal,
            'tax_rate': tax_rate,
            'tax_amount': tax_amount,
            'total': total,
            'status': status,
            'notes': notes,
            'created_at': created_at,
            'updated_at': updated_at
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({'error': 'Invoice number already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/invoices', methods=['GET'])
def list_invoices():
    status_filter = request.args.get('status')
    conn = get_db()
    c = conn.cursor()

    if status_filter:
        c.execute('''
            SELECT id, invoice_number, client_name, issue_date,
                   due_date, currency, total, status
            FROM invoices
            WHERE status = ?
            ORDER BY created_at DESC
        ''', (status_filter,))
    else:
        c.execute('''
            SELECT id, invoice_number, client_name, issue_date,
                   due_date, currency, total, status
            FROM invoices
            ORDER BY created_at DESC
        ''')

    rows = c.fetchall()
    conn.close()

    invoices = []
    for row in rows:
        invoices.append({
            'id': row['id'],
            'invoice_number': row['invoice_number'],
            'client_name': row['client_name'],
            'issue_date': row['issue_date'],
            'due_date': row['due_date'],
            'currency': row['currency'],
            'total': row['total'],
            'status': row['status']
        })

    return jsonify(invoices)

@app.route('/api/invoices/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM invoices WHERE id = ?
    ''', (invoice_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Invoice not found'}), 404

    invoice = dict(row)
    invoice['items'] = eval(invoice['items'])
    return jsonify(invoice)

@app.route('/api/invoices/<int:invoice_id>', methods=['PATCH'])
def update_invoice(invoice_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid payload'}), 400

    conn = get_db()
    c = conn.cursor()

    updates = []
    params = []

    if 'status' in data:
        updates.append('status = ?')
        params.append(data['status'])

    if 'client_name' in data:
        updates.append('client_name = ?')
        params.append(data['client_name'])

    if 'client_email' in data:
        updates.append('client_email = ?')
        params.append(data['client_email'])

    if 'issue_date' in data:
        updates.append('issue_date = ?')
        params.append(data['issue_date'])

    if 'due_date' in data:
        updates.append('due_date = ?')
        params.append(data['due_date'])

    if 'items' in data:
        items = data['items']
        subtotal, tax_amount, total = calculate_totals(items, data.get('tax_rate', 0.10))
        updates.append('items = ?')
        params.append(str(items))
        updates.append('subtotal = ?')
        params.append(subtotal)
        updates.append('tax_amount = ?')
        params.append(tax_amount)
        updates.append('total = ?')
        params.append(total)

    if 'notes' in data:
        updates.append('notes = ?')
        params.append(data['notes'])

    if 'tax_rate' in data:
        updates.append('tax_rate = ?')
        params.append(data['tax_rate'])

    if not updates:
        return jsonify({'error': 'No fields to update'}), 400

    updates.append('updated_at = ?')
    params.append(datetime.utcnow().isoformat())
    params.append(invoice_id)

    c.execute(f'''
        UPDATE invoices
        SET {', '.join(updates)}
        WHERE id = ?
    ''', params)

    conn.commit()
    conn.close()

    return jsonify({'message': 'Invoice updated'})

@app.route('/api/invoices/<int:invoice_id>', methods=['DELETE'])
def delete_invoice(invoice_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Invoice deleted'})

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return app.send_static_file(path)

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(host='0.0.0.0', port=5055, debug=True)
