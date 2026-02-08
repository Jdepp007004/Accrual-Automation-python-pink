"""
Flask Frontend for Accrual Automation
Provides web interface to trigger and monitor email processing workflows
"""

import os
import sys
import json
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv

# Add parent directory to path to import shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared_utils.google_auth import get_google_services

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-this')

# Webhook Configuration (points to Python webhook service)
WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook')


@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')


@app.route('/process-emails', methods=['GET', 'POST'])
def process_emails():
    """Process emails interface"""
    if request.method == 'GET':
        return render_template('process_emails.html')
    
    else:  # POST
        # Handle JSON request from frontend
        data = request.get_json()
        selected_labels = data.get('label_name', [])
        
        if not selected_labels:
            return jsonify({"error": "No labels selected"}), 400
        
        try:
            response = requests.post(
                f"{WEBHOOK_URL}/process-emails",
                json={"label_name": selected_labels},
                timeout=600  # 10 minutes timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return jsonify(result)
            else:
                return jsonify({"error": f"Processing failed: {response.text}"}), response.status_code
        
        except requests.exceptions.Timeout:
            return jsonify({"error": "Processing timed out. Check webhook service."}), 504
        except requests.exceptions.ConnectionError:
            return jsonify({"error": "Could not connect to webhook service. Make sure it's running on port 5678."}), 503
        except Exception as e:
            return jsonify({"error": f"Error: {str(e)}"}), 500


@app.route('/api/labels', methods=['GET'])
def get_labels():
    """API endpoint to get Gmail labels"""
    try:
        gmail, _, _, _ = get_google_services()
        all_labels = gmail.users().labels().list(userId="me").execute().get("labels", [])
        parent_labels = [
            lbl["name"] for lbl in all_labels
            if lbl.get("type") == "user" and "/" not in lbl["name"]
        ]
        return jsonify({"status": "success", "labels": sorted(parent_labels)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/manage-companies', methods=['GET', 'POST'])
def manage_companies():
    """Manage company aliases"""
    aliases_path = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'company_aliases.json')
    
    if request.method == 'GET':
        try:
            with open(aliases_path, 'r') as f:
                aliases = json.load(f)
            return render_template('manage_companies.html', companies=aliases)
        except Exception as e:
            return render_template('manage_companies.html', error=str(e), companies={})
    
    else:  # POST
        # Add/update company
        company_name = request.form.get('company_name')
        entity_type = request.form.get('entity_type', 'india')
        financial_year = request.form.get('financial_year', 'april-march')
        aliases = request.form.get('aliases', '').split(',')
        aliases = [a.strip() for a in aliases if a.strip()]
        
        try:
            with open(aliases_path, 'r') as f:
                companies = json.load(f)
            
            companies[company_name] = {
                "aliases": aliases,
                "financial_year": financial_year,
                "entity_type": entity_type
            }
            
            with open(aliases_path, 'w') as f:
                json.dump(companies, f, indent=4)
            
            flash(f'Company "{company_name}" saved successfully!', 'success')
            return redirect(url_for('manage_companies'))
        
        except Exception as e:
            return render_template('manage_companies.html', error=str(e), companies={})


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "accrual-automation-frontend"})


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5001))
    print(f"✨ Accrual Automation Frontend starting on port {port}")
    print(f"🌐 Open: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
