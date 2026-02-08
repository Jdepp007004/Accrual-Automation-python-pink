# N8N Accrual Automation Implementation

This is the n8n-based implementation of the Accrual Automation system, migrated from FastAPI. It uses n8n workflows for processing logic and a Flask frontend for user interaction.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [N8N Webhook Setup](#n8n-webhook-setup)
- [Flask Frontend Setup](#flask-frontend-setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Workflow Details](#workflow-details)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture Overview

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────────┐
│  Flask Frontend │────────▶│ N8N Webhooks │────────▶│  Google APIs    │
│  (Port 5001)    │         │ (Port 5678)  │         │  (Gmail, Drive, │
│                 │◀────────│              │◀────────│   Sheets, etc)  │
└─────────────────┘         └──────────────┘         └─────────────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │  Gemini AI   │
                            │  Analysis    │
                            └──────────────┘
```

- **Flask Frontend**: Web UI for triggering workflows and viewing data
- **N8N Workflows**: Visual automation workflows handling business logic
- **Google APIs**: Gmail, Drive, Sheets integration
- **Gemini AI**: Document analysis and data extraction

## ✅ Prerequisites

- **Python 3.10+** installed
- **N8N** already installed and running (self-hosted on port 5678)
- **Google Cloud credentials** (`credentials.json` in parent directory)
- **Google OAuth token** (`token.json` generated via `test_auth.py`)
- **Gemini API key** for document analysis

## 🚀 Installation

### 1. Setup Environment

Create a `.env` file in the `n8n_implementation` directory:

```bash
cd n8n_implementation
cp .env.example .env
```

Edit `.env` with your configuration:

```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook
FLASK_SECRET_KEY=your-random-secret-key-here
FLASK_PORT=5001
ROOT_FOLDER_ID=your-google-drive-root-folder-id
GEMINI_API_KEY=your-gemini-api-key
```

### 2. Install Flask Dependencies

```bash
cd flask_frontend
pip install -r requirements.txt
```

## 🔗 N8N Webhook Setup

### Required Webhooks

You need to create **ONE main webhook** in n8n for email processing. Here's how:

#### 1. Email Processing Webhook

**Webhook Path:** `/process-emails`

**In your n8n workflow:**

1. Add a **Webhook** node as the first node
2. Configure the webhook:
   - **HTTP Method**: `POST`
   - **Path**: `process-emails`
   - **Response Mode**: `When Last Node Finishes`
   - **Response Data**: `Last Node`

3. **Full Webhook URL will be:**
   ```
   http://localhost:5678/webhook/process-emails
   ```

#### Expected Request Format

The Flask frontend will send:

```json
{
  "label_name": ["TestLabel", "AnotherLabel"]
}
```

#### Workflow Steps (Overview)

Your n8n workflow should follow these steps:

1. **Webhook Trigger** - Receives label_name array
2. **Split Labels** - Loop through each label
3. **Load Config Files** - Read company_aliases.json and entity_folder_structures.json
4. **Gmail: Authenticate & Fetch** - Get emails with specified label
5. **Process Each Email** - Loop through threads/messages
6. **Extract Attachments** - Download each attachment
7. **Hash Check** - Verify not duplicate
8. **Gemini Analysis** - Analyze document with AI
9. **Upload to Drive** - Upload to appropriate folder
10. **Update Sheets** - Append data row
11. **Save Duplicates** - Update hash tracking
12. **Modify Labels** - Move email to Processed
13. **Webhook Response** - Return summary

### Using Python in N8N Code Nodes

You can import the shared utilities directly in n8n **Code** nodes:

```python
# Example n8n Code node
import sys
sys.path.insert(0, '/path/to/n8n_implementation')

from shared_utils.email_helpers import normalize_name, get_company_info
from shared_utils.google_auth import get_google_services
from shared_utils.file_helpers import compute_hash, build_updated_filename

# Your workflow logic here
gmail, sheets, drive, creds = get_google_services()
```

### Alternative: Copy Workflow JSON

I've created workflow JSON templates in the `workflows/` directory. You can:

1. Open n8n UI (http://localhost:5678)
2. Click **"Import from File"**
3. Select the workflow JSON file
4. Configure credentials
5. Activate workflow

> **Note**: The workflow JSONs are templates. You'll need to configure your Google OAuth credentials and Gemini API key within n8n for each node.

## 🌐 Flask Frontend Setup

### 1. Start the Flask Application

```bash
cd flask_frontend
python app.py
```

The Flask app will start on **port 5001** (configurable in `.env`).

### 2. Access the Dashboard

Open your browser and navigate to:

```
http://localhost:5001
```

### 3. Features Available

- **Dashboard** - Overview and quick actions
- **Process Emails** - Trigger email processing workflows
- **Manage Companies** - Add/update company aliases
- **Manage Folders** - View folder structures
- **View Logs** - Monitor application activity

## ⚙️ Configuration

### Company Aliases

Located in `../app/company_aliases.json` (shared with original FastAPI implementation).

Format:
```json
{
  "Company Name": {
    "aliases": ["Alias 1", "Alias 2"],
    "financial_year": "april-march",
    "entity_type": "india"
  }
}
```

### Folder Structures

Located in `../app/entity_folder_structures.json` (shared with original implementation).

Defines the Google Drive folder hierarchy for each entity type (india/us).

## 📖 Usage

### Processing Emails

1. Navigate to **Process Emails** page
2. Select one or more Gmail labels from the list
3. Click **"Start Processing"**
4. Wait for the workflow to complete
5. View processing summary and results

### Adding a Company

1. Go to **Manage Companies**
2. Fill in the form:
   - Company Name
   - Entity Type (India/US)
   - Financial Year
   - Aliases (comma-separated)
3. Click **"Save Company"**

### Viewing Logs

1. Navigate to **View Logs**
2. See the latest 100 log lines
3. Click **"Refresh"** to update

## 🔄 Workflow Details

### Email Processing Workflow

**Trigger**: POST request to `/webhook/process-emails`

**Key Operations**:
- Fetches emails from Gmail with specified labels
- Downloads and analyzes attachments using Gemini AI
- Uploads files to Google Drive with organized naming
- Logs extracted data to Google Sheets
- Tracks file hashes to prevent duplicate processing
- Moves processed emails to "Processed" label

**Expected Duration**: 2-5 minutes per label (depends on email count)

**Error Handling**: 
- Retries on rate limits
- Skips unsupported file types
- Continues processing even if individual files fail

### Data Flow

```
Gmail Email → Attachment → Gemini Analysis → Extract Data
                                    ↓
                            Drive Upload + Rename
                                    ↓
                          Sheets Row Append
                                    ↓
                       Update Duplicate Tracking
                                    ↓
                        Move to Processed Label
```

## 🐛 Troubleshooting

### Flask Frontend Issues

**Error: "Unable to fetch labels"**
- Check that `credentials.json` and `token.json` exist in parent directory
- Run `../test_auth.py` to regenerate token if expired

**Error: "N8N workflow failed"**
- Verify n8n is running: `http://localhost:5678`
- Check webhook URL in `.env` is correct
- View n8n execution logs in n8n UI

### N8N Workflow Issues

**Webhook returns 404**
- Ensure webhook node is configured with path: `process-emails`
- Workflow must be **activated** (toggle in n8n UI)

**Google API Authentication Fails**
- Configure Google OAuth credentials in n8n
- Add credentials to each Google node (Gmail, Drive, Sheets)

**Gemini API Errors**
- Verify `GEMINI_API_KEY` is set correctly
- Check API quota hasn't been exceeded
- Ensure you're using `gemini-2.0-flash-exp` model

### Common Solutions

1. **Restart n8n**: Sometimes webhooks need n8n restart to register
   ```bash
   # If running via npm
   n8n stop
   n8n start
   ```

2. **Check n8n Execution History**: 
   - Open n8n UI → Executions tab
   - View failed executions for error details

3. **Test Webhook Manually**:
   ```bash
   curl -X POST http://localhost:5678/webhook/process-emails \
     -H "Content-Type: application/json" \
     -d '{"label_name": ["TestLabel"]}'
   ```

## 🎯 Next Steps

1. **Import workflow templates** from `workflows/` directory
2. **Configure credentials** in n8n for Google APIs
3. **Test with a sample label** containing 1-2 test emails
4. **Monitor execution** in n8n UI
5. **Scale up** to production labels once verified

## 📚 Additional Resources

- [N8N Documentation](https://docs.n8n.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Google APIs Python Client](https://github.com/googleapis/google-api-python-client)
- [Gemini API Documentation](https://ai.google.dev/docs)

## 🔐 Security Notes

- Never commit `.env` file with actual credentials
- Keep `credentials.json` and `token.json` secure
- Use environment variables for sensitive data
- Consider adding authentication to Flask app for production

---

**Need help?** Check the logs or review n8n execution history for detailed error messages.
