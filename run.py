"""
Accrual Automation - Unified Runner
Single-file Flask application that processes emails, analyzes documents, and uploads to Google Drive.
No n8n or webhook service required - pure Python implementation.
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response
from dotenv import load_dotenv
import json
import uuid
import queue
import threading

# Add paths for imports
sys.path.insert(0, os.path.dirname(__file__))

from shared_utils.google_auth import get_google_services
from webhook_service.processors.email_processor import process_emails_workflow

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Initialize Flask app
app = Flask(__name__, 
            template_folder='flask_frontend/templates',
            static_folder='flask_frontend/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-this')

# Store active SSE streams
active_streams = {}


@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')


@app.route('/companies')
def companies():
    """Companies management page"""
    return render_template('companies.html')


@app.route('/stream-logs/<session_id>')
def stream_logs(session_id):
    """Server-Sent Events endpoint for streaming terminal output"""
    def generate():
        if session_id not in active_streams:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid session'})}\n\n"
            return
        
        msg_queue = active_streams[session_id]
        
        try:
            while True:
                try:
                    # Get message from queue (blocks for up to 30 seconds)
                    msg = msg_queue.get(timeout=30)
                    
                    if msg is None:  # Sentinel value to stop
                        break
                    
                    yield f"data: {json.dumps(msg)}\n\n"
                    
                except queue.Empty:
                    # Send keepalive ping
                    yield f": keepalive\n\n"
        finally:
            # Clean up
            if session_id in active_streams:
                del active_streams[session_id]
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/process-emails', methods=['GET', 'POST'])
def process_emails():
    """Process emails interface"""
    if request.method == 'GET':
        return render_template('process_emails.html')
    
    else:  # POST - Handle email processing
        data = request.get_json()
        selected_labels = data.get('label_name', [])
        
        if not selected_labels:
            return jsonify({"error": "No labels selected"}), 400
        
        # Create unique session ID for this processing run
        session_id = str(uuid.uuid4())
        msg_queue = queue.Queue()
        active_streams[session_id] = msg_queue
        
        # Run processing in background thread
        def process_in_background():
            try:
                # Call the processing workflow with queue for output
                result = process_emails_workflow(selected_labels, msg_queue)
                # Send completion event
                msg_queue.put({"type": "complete", "results": result})
            except Exception as e:
                msg_queue.put({"type": "error", "message": str(e)})
            finally:
                msg_queue.put(None)  # Sentinel to stop streaming
        
        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()
        
        # Return session ID immediately
        return jsonify({"session_id": session_id}), 200


@app.route('/update-folder-structures', methods=['POST'])
def update_folder_structures():
    """Update folder structures for all entities or specific entity"""
    from shared_utils.google_auth import get_google_services, find_or_create_folder
    from shared_utils.folder_management import validate_and_create_folder_structure
    
    data = request.get_json()
    entity_names = data.get('entities', [])  # Empty list means all entities
    
    # Get Google services
    gmail, sheets, drive, creds = get_google_services()
    
    # Load company aliases to get entity types
    import json
    aliases_path = os.path.join(os.path.dirname(__file__), 'company_aliases.json')
    with open(aliases_path, 'r') as f:
        company_aliases = json.load(f)
    
    # Get ROOT_FOLDER_ID
    ROOT_FOLDER_ID = os.getenv('ROOT_FOLDER_ID')
    
    results = []
    
    # If no specific entities, process all
    if not entity_names:
        entity_names = list(company_aliases.keys())
    
    for entity_name in entity_names:
        try:
            # Get entity info
            entity_info = company_aliases.get(entity_name, {})
            entity_type = entity_info.get('entity_type', 'india')
            
            # Find or create entity folder
            entity_folder_id = find_or_create_folder(drive, entity_name, ROOT_FOLDER_ID)
            
            # Validate and create folder structure
            result = validate_and_create_folder_structure(
                drive, entity_name, entity_folder_id, entity_type
            )
            results.append(result)
        except Exception as e:
            results.append({
                "entity": entity_name,
                "status": "error",
                "message": str(e)
            })
    
    return jsonify({
        "status": "completed",
        "results": results
    }), 200


@app.route('/get-companies', methods=['GET'])
def get_companies():
    """Get list of all companies from company_aliases.json"""
    try:
        aliases_path = os.path.join(os.path.dirname(__file__), 'company_aliases.json')
        with open(aliases_path, 'r') as f:
            companies = json.load(f)
        return jsonify(companies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/update-company', methods=['POST'])
def update_company():
    """Update company information in company_aliases.json"""
    try:
        data = request.get_json()
        aliases_path = os.path.join(os.path.dirname(__file__), 'company_aliases.json')
        
        # Read current data
        with open(aliases_path, 'r') as f:
            companies = json.load(f)
        
        # Update company data
        company_name = data.get('name')
        if company_name:
            companies[company_name] = {
                'aliases': data.get('aliases', []),
                'financial_year': data.get('financial_year', 'april-march'),
                'entity_type': data.get('entity_type', 'india')
            }
            
            # Write back to file
            with open(aliases_path, 'w') as f:
                json.dump(companies, f, indent=4)
            
            return jsonify({"status": "success", "message": f"Updated {company_name}"}), 200
        else:
            return jsonify({"error": "Company name is required"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    aliases_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'company_aliases.json')
    
    if request.method == 'GET':
        try:
            with open(aliases_path, 'r') as f:
                aliases = json.load(f)
            return render_template('manage_companies.html', companies=aliases)
        except Exception as e:
            return render_template('manage_companies.html', error=str(e), companies={})
    
    else:  # POST - Add/update company
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
    return jsonify({
        "status": "healthy", 
        "service": "accrual-automation-unified",
        "version": "2.0"
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5001))
    
    print("=" * 60)
    print("🚀 Accrual Automation - Unified Python Implementation")
    print("=" * 60)
    print(f"✨ Starting on: http://localhost:{port}")
    print(f"📁 Working directory: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"🔧 Environment loaded from: {os.path.join(os.path.dirname(__file__), '.env')}")
    print("=" * 60)
    print("📋 Available endpoints:")
    print(f"   • Dashboard: http://localhost:{port}/")
    print(f"   • Process Emails: http://localhost:{port}/process-emails")
    print(f"   • Manage Companies: http://localhost:{port}/manage-companies")
    print(f"   • Health Check: http://localhost:{port}/health")
    print("=" * 60)
    print("✅ Ready! Open your browser to get started.")
    print("💡 Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=port, debug=True)
