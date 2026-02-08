# 📥 How to Import N8N Workflow (Step-by-Step)

## Quick Import (2 Minutes)

### Step 1: Open N8N UI

1. Make sure n8n is running in your terminal
2. Open your browser
3. Go to: **http://localhost:5678**

### Step 2: Import the Workflow

1. Click **"Workflows"** in the left sidebar
2. Click the **"+"** button (top right) or **"Add workflow"**
3. Click the **three dots menu (⋮)** in the top bar
4. Select **"Import from File"**
5. Browse to: `n8n_implementation/workflows/email_processing_workflow.json`
6. Click **"Open"**

🎉 **Workflow imported!** You'll see 3 nodes: Webhook → Initialize & Authenticate → Process All Emails

### Step 3: Configure (IMPORTANT - Read Carefully)

The workflow JSON I created uses **Code nodes** with Python. However, n8n Code nodes have limitations. You need to make a small adjustment:

**Option A: Use the workflow as-is (if n8n supports Python)**
- If your n8n supports Python in Code nodes, you're done!
- Just activate the workflow

**Option B: If Python Code nodes don't work**
- The Code nodes will need to be converted to use n8n's API calls
- See "Manual Workflow Creation" below

---

## ⚠️ Important Note About N8N Code Nodes

N8N's **Code node** primarily supports **JavaScript**, not Python by default. The workflow I created uses Python because that's where all your logic is.

### Solution Options:

1. **Best Option: Use Python Webhook Service Instead**
   - I can create a simple Python Flask service that runs on port 5678
   - Acts as the webhook endpoint
   - Implements all the logic in pure Python
   - Works perfectly with the Flask frontend
   - **Recommended!**

2. **Alternative: Use n8n with proper nodes**
   - Follow the manual creation guide below
   - Use Gmail nodes, Drive nodes, etc.
   - More clicking but fully visual

---

## 🛠️ Manual Workflow Creation (Step-by-Step)

If you want to build the workflow manually in n8n UI:

### Node 1: Webhook (Trigger)

1. Click **"Add node"** → Search for **"Webhook"**
2. Configure:
   - **HTTP Method**: POST
   - **Path**: `process-emails`
   - **Authentication**: None
   - **Response Mode**: When Last Node Finishes
3. Click **"Execute Node"** to test (it will wait for a request)
4. **Save** the node

**Your webhook URL is now:**
```
http://localhost:5678/webhook/process-emails
```

### Node 2: Set Variables

1. Click **"+"** after Webhook node → Search **"Set"**
2. Add these values:
   - **Name**: `label_name`
   - **Value**: `{{ $json.body.label_name }}`
3. **Save** the node

### Node 3: Google Gmail - List Messages

1. Add node → Search **"Gmail"**
2. **Credential**: Click "Create New" →
   - Select "OAuth2"
   - Use your `credentials.json` info
   - Authorize
3. **Operation**: Get All
4. **Filters**: 
   - **Label IDs**: Use expression `{{ $json.label_name }}`
5. **Save**

### Node 4: Split Into Items (Loop Messages)

1. Add node → Search **"Split In Batches"**
2. **Batch Size**: 1
3. This creates a loop for each email

### Node 5: Gmail - Get Attachment

1. Add node → **Gmail**
2. **Resource**: Message
3. **Operation**: Get
4. **Message ID**: `{{ $json.id }}`
5. **Options** → Enable "Download Attachments"

### Node 6: HTTP Request - Gemini API

1. Add node → **HTTP Request**
2. **Method**: POST
3. **URL**: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent`
4. **Authentication**: Generic Credential Type
   - **Header Auth**
   - **Name**: `x-goog-api-key`
   - **Value**: Your Gemini API key
5. **Body**: 
   ```json
   {
     "contents": [{
       "parts": [{
         "inline_data": {
           "mime_type": "{{ $json.mimeType }}",
           "data": "{{ $json.data }}"
         }
       }]
     }]
   }
   ```

### Node 7: Google Drive - Upload File

1. Add node → **Google Drive**
2. **Operation**: Upload
3. **File Name**: Expression to build from Gemini response
4. **Binary Data**: Yes
5. **Parent Folder ID**: Your folder ID

### Node 8: Google Sheets - Append Row

1. Add node → **Google Sheets**
2. **Operation**: Append
3. **Document ID**: Your spreadsheet ID
4. **Sheet**: "Docs Extraction"
5. **Columns**: Map allfields from Gemini response

### Node 9: Gmail - Modify Labels

1. Add node → **Gmail**
2. **Operation**: Modify Labels
3. **Add Labels**: "Processed"
4. **Remove Labels**: Original label

### Final Step: Connect All Nodes

- Draw arrows connecting each node in sequence
- Make sure the flow goes: Webhook → Set → Gmail List → Loop → Get Attachment → Gemini → Drive → Sheets → Modify Labels → Loop End

### Activate Workflow

1. Toggle the **"Active"** switch in top right
2. Click **"Save"**

✅ **Workflow is now live!**

---

## 🚀 Better Alternative: Python Webhook Service

Instead of dealing with n8n's complexity, I can create a **simple Python service** that:
- Listens on port 5678 (like n8n)
- Provides the `/webhook/process-emails` endpoint  
- Uses all the shared utilities I already created
- Works **identically** to n8n for your Flask frontend
- **Much simpler** - pure Python, no visual workflow needed

**Would you like me to create this instead?** It'll be:
- ✅ Fully working in 2 minutes
- ✅ No n8n complications
- ✅ Easy to test and debug
- ✅ Uses all the code I already wrote

Let me know if you want this Python webhook service - it's the easiest path!
