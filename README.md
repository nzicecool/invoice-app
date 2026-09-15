# Invoice App

Simple invoice creation web app for Raspberry Pi 4 (arm64).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app runs at http://0.0.0.0:5055 and is accessible from your LAN at `http://<pi-ip>:5055`.

## Usage

- Create invoices via the web interface
- Edit status (draft/sent/paid/overdue)
- Print invoices from the invoice view page
