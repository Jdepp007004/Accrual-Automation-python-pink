# Python Webhook Service - Quick Start

This Python service runs on **port 5678** and provides the same webhook endpoint that n8n would provide.

## 🚀 Start the Service

```bash
cd webhook_service
pip install -r requirements.txt
python app.py
```

The service will start on: **http://localhost:5678**

## 📍 Endpoints

### `/webhook/process-emails` (POST)
Main endpoint for email processing.

**Request:**
```json
{
  "label_name": ["TestLabel", "AnotherLabel"]
}
```

**Response:**
```json
{
  "status": "completed",
  "details": [
    {
      "entity": "TestLabel",
      "status": "success",
      "threads_processed": 5,
      "attachments_added": 12,
      "skipped_files": []
    }
  ]
}
```

### `/webhook/health` (GET)
Health check endpoint.

### `/webhook/test` (POST)
Test endpoint to verify webhook is working.

## 🔧 How It Works

1. **Flask app** listens on port 5678 (same as n8n)
2. **Receives webhook** from Flask frontend
3. **Calls email_processor** with label names  
4. **Returns results** to frontend

## 📁 Structure

```
webhook_service/
├── app.py                      # Main Flask webhook service
├── processors/
│   └── email_processor.py      # Email processing logic
└── requirements.txt            # Python dependencies
```

## 🔄 Migration to N8N

When ready to migrate to n8n:

1. Stop this Python service
2. Start n8n (port 5678)
3. Import workflow from `../workflows/`
4. Use JavaScript wrappers from `../n8n_js_wrappers/`

The Flask frontend doesn't need any changes!

## 📝 Notes

- Uses the same **shared_utils** as Flask frontend
- Shares **configuration files** with original FastAPI
- **Modular design** - easy to add new processors
- **N8N-ready** - can migrate without changing logic

## 🧪 Testing

Test with curl:
```bash
curl -X POST http://localhost:5678/webhook/process-emails \
  -H "Content-Type: application/json" \
  -d '{"label_name": ["TestLabel"]}'
```

Or use the Flask frontend at http://localhost:5001
