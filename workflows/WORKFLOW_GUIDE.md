# N8N Workflow Documentation

## Webhook Configuration

For your n8n webhook node, use the following configuration:

### Webhook Node Settings

```
HTTP Method: POST
Path: process-emails
Response Mode: When Last Node Finishes
Response Data: Last Node
Authentication: None (can add later if needed)
```

### Full Webhook URL

```
http://localhost:5678/webhook/process-emails
```

Update your `.env` file to point to this URL.

## Workflow Structure (Email Processing)

Since n8n workflows are best created visually, here's the recommended node sequence:

### 1. Webhook (Trigger)
- **Type**: Webhook
- **Method**: POST
- **Path**: `process-emails`
- **Input**: Expects `{ "label_name": ["Label1", "Label2"] }`

### 2. Split In Batches
- **Type**: Split In Batches
- **Batch Size**: 1
- **Expression**: `{{ $json.label_name }}`
- Loops through each label name

### 3. Set Variables
- **Type**: Set
- Create variables for:
  - `current_label` = `{{ $json.label_name }}`
  - `credentials_path` = Full path to credentials.json
  - `token_path` = Full path to token.json

### 4. Execute Python Script (Load Config)
- **Type**: Code
- **Language**: Python
- Load company_aliases.json and entity_folder_structures.json
- Read environment variables

### 5. Gmail: List Messages
- **Type**: Gmail node
- **Operation**: Get All Messages
- **Filter**: `labelIds: {{ $node["Set Variables"].json["label_id"] }}`

### 6. Loop Messages (Split In Batches)
- Batch size: 1
- Process each message individually

### 7. Gmail: Get Attachment
- **Type**: Gmail node
- **Operation**: Get Attachment
- Download each attachment from message

### 8. Code: Check Duplicates
- **Type**: Code
- **Language**: Python
- Compute file hash
- Check against Drive .metadata folder
- Skip if duplicate found

### 9. HTTP Request: Gemini API
- **Type**: HTTP Request
- **Method**: POST
- **URL**: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent`
- **Authentication**: API Key
- **Body**: Include file data and prompt

### 10. Code: Parse Gemini Response
- **Type**: Code
- Extract JSON from Gemini response
- Handle multiple documents if present

### 11. Google Drive: Upload File
- **Type**: Google Drive node
- **Operation**: Upload
- **Parent Folder**: Determine based on entity type and folder structure

### 12. Google Sheets: Append Row
- **Type**: Google Sheets node
- **Operation**: Append
- **Sheet**: "Docs Extraction"
- Map all fields from Gemini analysis

### 13. Google Drive: Update Duplicates JSON
- **Type**: Google Drive node
- **Operation**: Upload/Update
- Save file hash to .metadata folder

### 14. Gmail: Modify Labels
- **Type**: Gmail node
- **Operation**: Modify Labels
- Add "Processed" label
- Remove original trigger label

### 15. Merge Back (If using loops)
- **Type**: Merge
- Combines all processed results

### 16. Format Response
- **Type**: Function or Code
- Prepare summary JSON response
- Include counts: threads_processed, attachments_added, skipped_files

## Creating the Workflow

### Option 1: Manual Creation in N8N UI

1. Open n8n UI (http://localhost:5678)
2. Click "Add Workflow" 
3. Add nodes in the sequence above
4. Connect nodes with arrows
5. Configure each node's parameters
6. Test with sample data
7. Save and activate

### Option 2: Using Code Nodes for Python

For complex logic, use **Code** nodes with Python:

```python
# Example Code node for processing
import sys
import os
import json

# Add path to shared utilities
sys.path.insert(0, '/full/path/to/n8n_implementation')

from shared_utils.google_auth import get_google_services
from shared_utils.email_helpers import get_company_info, normalize_name
from shared_utils.file_helpers import compute_hash, build_updated_filename
from shared_utils.gemini_client import analyze_document_with_gemini

# Get services
gmail, sheets, drive, creds = get_google_services()

# Your processing logic here
label_name = $input.all()[0].json['label_name']

# Return results
return [{
    "json": {
        "status": "success",
        "label": label_name
    }
}]
```

## Environment Variables in N8N

You can set environment variables for n8n:

### For n8n running as service:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
export GEMINI_API_KEY=your-api-key
```

### For n8n via npm:
Create `.env` file in n8n directory or set variables before starting:
```bash
GEMINI_API_KEY=your-key n8n start
```

## Testing Your Workflow

1. **Test Mode**: Click "Execute Workflow" button in n8n UI
2. **Provide Test Data**:
   ```json
   {
     "label_name": ["TestLabel"]
   }
   ```
3. **Check Each Node**: View output of each node step-by-step
4. **Fix Errors**: Update node configuration if errors occur
5. **Activate**: Once working, activate the workflow

## Webhook Testing from Command Line

```bash
# Test the webhook manually
curl -X POST http://localhost:5678/webhook/process-emails \
  -H "Content-Type: application/json" \
  -d '{"label_name": ["YourTestLabel"]}'
```

## Important Notes

- **Paths**: Update all file paths to match your system
- **Credentials**: Configure Google OAuth in n8n UI under "Credentials"
- **Timeouts**: Set appropriate timeouts for long-running operations
- **Error Handling**: Use "Continue On Fail" option for error handling
- **Logging**: Enable workflow execution logging in n8n settings

## Additional Workflow Ideas

You can create separate workflows for:

1. **Scheduled Processing**: Add a Cron trigger to process emails daily
2. **Slack Notifications**: Add Slack node to notify on completion
3. **Error Handling**: Create error workflow triggered on failures
4. **Backup**: Workflow to backup metadata and configurations

## Workflow Import/Export

### To Export:
1. Open workflow in n8n
2. Click workflow menu (3 dots)
3. Select "Download"
4. Save JSON file

### To Share:
Place JSON files in `workflows/` directory for version control and sharing.
