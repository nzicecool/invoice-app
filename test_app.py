import pytest
import json
from datetime import datetime
from app import app, get_db, calculate_totals, init_db
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    db_path = 'test_invoices.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    app.config['DB_PATH'] = db_path
    client = app.test_client()

    with app.app_context():
        init_db()

    yield client

    if os.path.exists(db_path):
        os.remove(db_path)

def test_create_invoice(client):
    payload = {
        'invoice_number': 'INV-0001',
        'client_name': 'Test Client',
        'client_email': 'test@example.com',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'currency': 'AUD',
        'items': [
            {'description': 'Service', 'qty': 2, 'unit_price': 100}
        ],
        'tax_rate': 0.10,
        'notes': 'Test invoice',
        'status': 'draft'
    }

    response = client.post('/api/invoices', json=payload)
    assert response.status_code == 201

    data = response.get_json()
    assert data['invoice_number'] == 'INV-0001'
    assert data['client_name'] == 'Test Client'
    assert data['total'] == 220.00  # 200 + 20 tax
    assert data['status'] == 'draft'

def test_create_invoice_without_required_fields(client):
    payload = {
        'client_name': 'Test Client'
    }

    response = client.post('/api/invoices', json=payload)
    assert response.status_code == 400

def test_create_duplicate_invoice_number(client):
    payload1 = {
        'invoice_number': 'INV-0001',
        'client_name': 'Client 1',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 1, 'unit_price': 100}]
    }

    payload2 = {
        'invoice_number': 'INV-0001',
        'client_name': 'Client 2',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 1, 'unit_price': 100}]
    }

    client.post('/api/invoices', json=payload1)
    response = client.post('/api/invoices', json=payload2)

    assert response.status_code == 400

def test_list_invoices(client):
    payload = {
        'invoice_number': 'INV-0001',
        'client_name': 'Client 1',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 1, 'unit_price': 100}]
    }

    client.post('/api/invoices', json=payload)

    response = client.get('/api/invoices')
    assert response.status_code == 200

    data = response.get_json()
    assert len(data) == 1
    assert data[0]['invoice_number'] == 'INV-0001'

def test_list_invoices_filtered_by_status(client):
    payload1 = {
        'invoice_number': 'INV-0001',
        'client_name': 'Client 1',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 1, 'unit_price': 100}],
        'status': 'sent'
    }

    payload2 = {
        'invoice_number': 'INV-0002',
        'client_name': 'Client 2',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 1, 'unit_price': 100}],
        'status': 'paid'
    }

    client.post('/api/invoices', json=payload1)
    client.post('/api/invoices', json=payload2)

    response = client.get('/api/invoices?status=sent')
    assert response.status_code == 200

    data = response.get_json()
    assert len(data) == 1
    assert data[0]['status'] == 'sent'

def test_get_invoice(client):
    payload = {
        'invoice_number': 'INV-0001',
        'client_name': 'Test Client',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 2, 'unit_price': 100}]
    }

    client.post('/api/invoices', json=payload)

    response = client.get('/api/invoices/1')
    assert response.status_code == 200

    data = response.get_json()
    assert data['invoice_number'] == 'INV-0001'
    assert data['client_name'] == 'Test Client'
    assert len(data['items']) == 1
    assert data['total'] == 220.00

def test_get_nonexistent_invoice(client):
    response = client.get('/api/invoices/999')
    assert response.status_code == 404

def test_update_invoice(client):
    payload = {
        'invoice_number': 'INV-0001',
        'client_name': 'Original Client',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 1, 'unit_price': 100}]
    }

    client.post('/api/invoices', json=payload)

    update_payload = {
        'status': 'paid',
        'client_name': 'Updated Client'
    }

    response = client.patch('/api/invoices/1', json=update_payload)
    assert response.status_code == 200

    get_response = client.get('/api/invoices/1')
    data = get_response.get_json()
    assert data['client_name'] == 'Updated Client'
    assert data['status'] == 'paid'

def test_update_invoice_with_items(client):
    payload = {
        'invoice_number': 'INV-0001',
        'client_name': 'Client 1',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 1, 'unit_price': 100}]
    }

    client.post('/api/invoices', json=payload)

    update_payload = {
        'items': [
            {'description': 'Service 1', 'qty': 2, 'unit_price': 100},
            {'description': 'Service 2', 'qty': 1, 'unit_price': 50}
        ],
        'tax_rate': 0.10
    }

    response = client.patch('/api/invoices/1', json=update_payload)
    assert response.status_code == 200

    get_response = client.get('/api/invoices/1')
    data = get_response.get_json()
    assert len(data['items']) == 2
    assert data['total'] == 275.00  # 250 subtotal + 25 tax

def test_delete_invoice(client):
    payload = {
        'invoice_number': 'INV-0001',
        'client_name': 'Test Client',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 1, 'unit_price': 100}]
    }

    client.post('/api/invoices', json=payload)

    response = client.delete('/api/invoices/1')
    assert response.status_code == 200

    get_response = client.get('/api/invoices/1')
    assert get_response.status_code == 404

def test_calculate_totals():
    items = [
        {'description': 'Service', 'qty': 2, 'unit_price': 100},
        {'description': 'Product', 'qty': 3, 'unit_price': 50}
    ]

    subtotal, tax_amount, total = calculate_totals(items, 0.10)

    assert subtotal == 350.00  # 2*100 + 3*50
    assert tax_amount == 35.00
    assert total == 385.00

def test_calculate_totals_no_tax():
    items = [
        {'description': 'Service', 'qty': 1, 'unit_price': 100}
    ]

    subtotal, tax_amount, total = calculate_totals(items, 0.00)

    assert subtotal == 100.00
    assert tax_amount == 0.00
    assert total == 100.00

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Invoice App' in response.data
    assert b'app.js' in response.data

def test_static_file(client):
    response = client.get('/static/index.html')
    assert response.status_code == 200
    assert b'<!DOCTYPE html>' in response.data

def test_invoice_validation_currency(client):
    payload = {
        'invoice_number': 'INV-0001',
        'client_name': 'Test Client',
        'issue_date': '2024-01-15',
        'due_date': '2024-02-15',
        'items': [{'description': 'Service', 'qty': 1, 'unit_price': 100}]
    }

    response = client.post('/api/invoices', json=payload)
    assert response.status_code == 201

    get_response = client.get('/api/invoices/1')
    data = get_response.get_json()
    assert data['currency'] == 'AUD'
