"""
Python Webhook Service - Mimics N8N on port 5678
Provides /webhook/process-emails endpoint
Can be replaced with n8n workflows later using the JS wrappers
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from processors.email_processor import process_emails_workflow

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)
CORS(app)

@app.route('/webhook/process-emails', methods=['POST'])
def process_emails():
    """
    Main webhook endpoint for email processing.
    This endpoint mimics n8n's webhook functionality.
    """
    try:
        data = request.get_json()
        label_names = data.get('label_name', [])
        
        if not label_names:
            return jsonify({
                'status': 'error',
                'message': 'No labels provided'
            }), 400
        
        # Call the processor (modular Python function)
        result = process_emails_workflow(label_names)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/webhook/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'python-webhook-service',
        'port': 5678
    })


@app.route('/webhook/test', methods=['POST'])
def test():
    """Test endpoint to verify webhook is working"""
    data = request.get_json()
    return jsonify({
        'status': 'success',
        'message': 'Webhook is working!',
        'received_data': data
    })


if __name__ == '__main__':
    port = 5678  # Same port as n8n
    print(f"🚀 Python Webhook Service starting on port {port}")
    print(f"📍 Webhook URL: http://localhost:{port}/webhook/process-emails")
    print(f"💚 Health check: http://localhost:{port}/webhook/health")
    print(f"\n⚡ Ready to receive requests from Flask frontend!")
    
    app.run(host='0.0.0.0', port=port, debug=True)
