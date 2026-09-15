let currentInvoice = null;
let editingId = null;

document.addEventListener('DOMContentLoaded', () => {
    loadInvoices();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('newInvoiceBtn').addEventListener('click', showNewInvoiceForm);
    document.getElementById('addItemBtn').addEventListener('click', addItemRow);
    document.getElementById('saveBtn').addEventListener('click', saveInvoice);
    document.getElementById('cancelBtn').addEventListener('click', showInvoiceList);
    document.getElementById('printBtn').addEventListener('click', printInvoice);
    document.getElementById('backToList').addEventListener('click', showInvoiceList);
    document.getElementById('markSentBtn').addEventListener('click', () => updateStatus('sent'));
    document.getElementById('markPaidBtn').addEventListener('click', () => updateStatus('paid'));
    document.getElementById('editInvoiceBtn').addEventListener('click', () => showInvoiceForm(editingId));
    document.getElementById('deleteInvoiceBtn').addEventListener('click', deleteInvoice);
    document.getElementById('statusFilter').addEventListener('change', loadInvoices);
    document.getElementById('gstToggle').addEventListener('change', updateTotals);
}

function showInvoiceList() {
    document.getElementById('invoiceList').style.display = 'block';
    document.getElementById('invoiceForm').style.display = 'none';
    document.getElementById('invoiceView').style.display = 'none';
    document.getElementById('printBtn').style.display = 'none';
    loadInvoices();
}

function showNewInvoiceForm() {
    currentInvoice = {
        invoice_number: 'INV-' + String(Date.now()).slice(-6),
        client_name: '',
        client_email: '',
        issue_date: new Date().toISOString().split('T')[0],
        due_date: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        currency: 'AUD',
        items: [{ description: '', qty: 1, unit_price: 0 }],
        tax_rate: 0.10,
        notes: '',
        status: 'draft'
    };
    editingId = null;
    renderInvoiceForm();
    document.getElementById('invoiceList').style.display = 'none';
    document.getElementById('invoiceForm').style.display = 'block';
    document.getElementById('invoiceView').style.display = 'none';
    document.getElementById('formTitle').textContent = 'New Invoice';
    document.getElementById('printBtn').style.display = 'none';
}

function showInvoiceForm(id) {
    fetch(`/api/invoices/${id}`)
        .then(response => {
            if (!response.ok) throw new Error('Invoice not found');
            return response.json();
        })
        .then(invoice => {
            currentInvoice = invoice;
            editingId = id;
            renderInvoiceForm();
            document.getElementById('invoiceList').style.display = 'none';
            document.getElementById('invoiceForm').style.display = 'block';
            document.getElementById('invoiceView').style.display = 'none';
            document.getElementById('formTitle').textContent = 'Edit Invoice';
            document.getElementById('printBtn').style.display = 'inline-block';
        })
        .catch(error => {
            alert(error.message);
            showInvoiceList();
        });
}

function showInvoiceView(id) {
    fetch(`/api/invoices/${id}`)
        .then(response => {
            if (!response.ok) throw new Error('Invoice not found');
            return response.json();
        })
        .then(invoice => {
            editingId = id;
            renderInvoiceView(invoice);
            document.getElementById('invoiceList').style.display = 'none';
            document.getElementById('invoiceForm').style.display = 'none';
            document.getElementById('invoiceView').style.display = 'block';
        })
        .catch(error => {
            alert(error.message);
            showInvoiceList();
        });
}

function renderInvoiceForm() {
    document.getElementById('invoiceId').value = currentInvoice.id || '';
    document.getElementById('invoiceNumber').value = currentInvoice.invoice_number || '';
    document.getElementById('clientName').value = currentInvoice.client_name || '';
    document.getElementById('clientEmail').value = currentInvoice.client_email || '';
    document.getElementById('issueDate').value = currentInvoice.issue_date || '';
    document.getElementById('dueDate').value = currentInvoice.due_date || '';
    document.getElementById('currency').value = currentInvoice.currency || 'AUD';
    document.getElementById('notes').value = currentInvoice.notes || '';

    const gstToggle = document.getElementById('gstToggle');
    gstToggle.checked = currentInvoice.tax_rate > 0;
    document.getElementById('gstRateDisplay').textContent = Math.round(currentInvoice.tax_rate * 100);

    renderItems(currentInvoice.items || [{ description: '', qty: 1, unit_price: 0 }]);
    updateTotals();
}

function renderItems(items) {
    const container = document.getElementById('itemsContainer');
    container.innerHTML = '';

    items.forEach((item, index) => {
        const row = document.createElement('div');
        row.className = 'item-row';
        row.innerHTML = `
            <input type="text" placeholder="Description" value="${item.description || ''}" data-index="${index}" class="description">
            <input type="number" min="0" step="0.01" placeholder="Qty" value="${item.qty || 1}" data-index="${index}" class="qty">
            <input type="number" min="0" step="0.01" placeholder="Price" value="${item.unit_price || 0}" data-index="${index}" class="price">
            <div class="subtotal">$${calculateItemSubtotal(item).toFixed(2)}</div>
            <button type="button" class="remove-item" data-index="${index}">×</button>
        `;
        container.appendChild(row);
    });

    container.querySelectorAll('.remove-item').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.target.dataset.index);
            const items = getCurrentItems();
            if (items.length > 1) {
                items.splice(index, 1);
                renderItems(items);
                updateTotals();
            }
        });
    });

    container.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', () => {
            const index = parseInt(input.dataset.index);
            const items = getCurrentItems();
            items[index][input.className] = parseFloat(input.value) || 0;
            renderItems(items);
            updateTotals();
        });
    });
}

function getCurrentItems() {
    const container = document.getElementById('itemsContainer');
    const items = [];
    container.querySelectorAll('.item-row').forEach(row => {
        items.push({
            description: row.querySelector('.description').value,
            qty: parseFloat(row.querySelector('.qty').value) || 0,
            unit_price: parseFloat(row.querySelector('.price').value) || 0
        });
    });
    return items;
}

function addItemRow() {
    const items = getCurrentItems();
    items.push({ description: '', qty: 1, unit_price: 0 });
    renderItems(items);
    updateTotals();
}

function calculateItemSubtotal(item) {
    return (item.qty || 0) * (item.unit_price || 0);
}

function updateTotals() {
    const items = getCurrentItems();
    const gstToggle = document.getElementById('gstToggle');
    const taxRate = gstToggle.checked ? 0.10 : 0;
    const subtotal = items.reduce((sum, item) => sum + calculateItemSubtotal(item), 0);
    const taxAmount = subtotal * taxRate;
    const total = subtotal + taxAmount;

    document.getElementById('subtotalDisplay').textContent = formatCurrency(subtotal);
    document.getElementById('gstDisplay').textContent = formatCurrency(taxAmount);
    document.getElementById('totalDisplay').textContent = formatCurrency(total);

    if (currentInvoice) {
        currentInvoice.items = items;
        currentInvoice.tax_rate = taxRate;
    }
}

function formatCurrency(amount) {
    return '$' + amount.toFixed(2);
}

function loadInvoices() {
    const statusFilter = document.getElementById('statusFilter').value;
    const url = statusFilter ? `/api/invoices?status=${statusFilter}` : '/api/invoices';

    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load invoices');
            return response.json();
        })
        .then(invoices => {
            renderInvoiceList(invoices);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to load invoices');
        });
}

function renderInvoiceList(invoices) {
    const table = document.getElementById('invoicesTable');
    table.innerHTML = '';

    if (invoices.length === 0) {
        table.innerHTML = '<p>No invoices found.</p>';
        return;
    }

    const tableHTML = `
        <table>
            <thead>
                <tr>
                    <th>Invoice Number</th>
                    <th>Client</th>
                    <th>Total</th>
                    <th>Due Date</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${invoices.map(invoice => `
                    <tr data-id="${invoice.id}">
                        <td><strong>${invoice.invoice_number}</strong></td>
                        <td>${escapeHtml(invoice.client_name)}</td>
                        <td>${formatCurrency(invoice.total)}</td>
                        <td>${invoice.due_date}</td>
                        <td><span class="status-pill status-${invoice.status}">${invoice.status.toUpperCase()}</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    table.innerHTML = tableHTML;

    table.querySelectorAll('tbody tr').forEach(row => {
        row.addEventListener('click', () => {
            const id = parseInt(row.dataset.id);
            showInvoiceView(id);
        });
    });
}

function renderInvoiceView(invoice) {
    document.getElementById('viewInvoiceNumber').textContent = invoice.invoice_number;
    document.getElementById('viewIssueDate').textContent = invoice.issue_date;
    document.getElementById('viewDueDate').textContent = invoice.due_date;
    document.getElementById('viewClientName').textContent = invoice.client_name;
    document.getElementById('viewClientEmail').textContent = invoice.client_email || '';
    document.getElementById('viewStatus').textContent = invoice.status.toUpperCase();
    document.getElementById('viewStatus').className = `status-pill status-${invoice.status}`;

    const tbody = document.getElementById('viewItemsBody');
    tbody.innerHTML = invoice.items.map(item => `
        <tr>
            <td>${escapeHtml(item.description)}</td>
            <td>${item.qty}</td>
            <td>${formatCurrency(item.unit_price)}</td>
            <td>${formatCurrency(calculateItemSubtotal(item))}</td>
        </tr>
    `).join('');

    document.getElementById('viewSubtotal').textContent = formatCurrency(invoice.subtotal);
    document.getElementById('viewTax').textContent = formatCurrency(invoice.tax_amount);
    document.getElementById('viewTotal').textContent = formatCurrency(invoice.total);

    const notes = document.getElementById('viewNotes');
    notes.style.display = invoice.notes ? 'block' : 'none';
    notes.textContent = invoice.notes || '';
}

async function saveInvoice() {
    const invoiceNumber = document.getElementById('invoiceNumber').value.trim();
    const clientName = document.getElementById('clientName').value.trim();
    const issueDate = document.getElementById('issueDate').value;
    const dueDate = document.getElementById('dueDate').value;
    const currency = document.getElementById('currency').value;
    const notes = document.getElementById('notes').value.trim();
    const gstToggle = document.getElementById('gstToggle');

    if (!invoiceNumber) {
        alert('Invoice number is required');
        return;
    }

    if (!clientName) {
        alert('Client name is required');
        return;
    }

    if (!issueDate) {
        alert('Issue date is required');
        return;
    }

    if (!dueDate) {
        alert('Due date is required');
        return;
    }

    const items = getCurrentItems();
    const taxRate = gstToggle.checked ? 0.10 : 0;
    const subtotal = items.reduce((sum, item) => sum + calculateItemSubtotal(item), 0);
    const taxAmount = subtotal * taxRate;
    const total = subtotal + taxAmount;

    const invoiceData = {
        invoice_number: invoiceNumber,
        client_name: clientName,
        client_email: document.getElementById('clientEmail').value.trim(),
        issue_date: issueDate,
        due_date: dueDate,
        currency: currency,
        items: items,
        tax_rate: taxRate,
        tax_amount: taxAmount,
        total: total,
        notes: notes,
        status: editingId ? currentInvoice.status : 'draft'
    };

    try {
        const url = editingId ? `/api/invoices/${editingId}` : '/api/invoices';
        const method = editingId ? 'PATCH' : 'POST';
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(invoiceData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to save invoice');
        }

        const savedInvoice = await response.json();
        currentInvoice = savedInvoice;

        if (editingId) {
            alert('Invoice updated successfully!');
        } else {
            editingId = savedInvoice.id;
            document.getElementById('formTitle').textContent = 'Edit Invoice';
            document.getElementById('printBtn').style.display = 'inline-block';
        }

        showInvoiceView(savedInvoice.id);
    } catch (error) {
        alert(error.message);
    }
}

async function updateStatus(status) {
    try {
        const response = await fetch(`/api/invoices/${editingId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update status');
        }

        alert('Status updated successfully!');
        showInvoiceView(editingId);
    } catch (error) {
        alert(error.message);
    }
}

async function deleteInvoice() {
    if (!confirm('Are you sure you want to delete this invoice?')) {
        return;
    }

    try {
        const response = await fetch(`/api/invoices/${editingId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete invoice');
        }

        alert('Invoice deleted successfully!');
        showInvoiceList();
    } catch (error) {
        alert(error.message);
    }
}

function printInvoice() {
    window.print();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
