# 📋 Complete N8N Migration Guide - Step by Step

## 🎯 Overview

This guide will walk you through migrating from the **Python Webhook Service** to **N8N**, while keeping all your Python logic intact using JavaScript wrappers.

---

## 📊 Current vs Future Architecture

### Current (Phase 1 - Working Now)
```
Flask Frontend → Python Webhook Service → Shared Utils → Google APIs
  (port 5001)         (port 5678)                          Gemini AI
```

### After Migration (Phase 2)
```
Flask Frontend → N8N Workflows → JS Wrappers → Python Scripts → Google APIs
  (port 5001)      (port 5678)                                    Gemini AI
```

**Key Point:** Your Python logic stays the same! JavaScript just calls it.

---

## ✅ Prerequisites

Before starting, ensure you have:

- ✅ Python webhook service working (you have this!)
- ✅ N8N installed and working
- ✅ Node.js installed (for n8n)
- ✅ All Python dependencies installed
- ✅ Google credentials configured

---

## 🚀 Migration Steps

### Step 1: Stop Python Webhook Service

**Action:**
1. Go to the terminal running the Python webhook service
2. Press `Ctrl+C` to stop it
3. Verify it stopped: `http://localhost:5678` should not respond

**Why:** N8N needs to use port 5678. Only one service can use a port at a time.

---

### Step 2: Start N8N

**Option A: If N8N is installed globally**
```bash
# Open a new terminal
n8n start
```

**Option B: If using npm**
```bash
npm install -g n8n
n8n start
```

**Option C: If using Docker**
```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

**Expected Output:**
```
Editor is now accessible via:
http://localhost:5678/
```

**Verify:**
- Open browser: `http://localhost:5678`
- You should see the n8n UI

---

### Step 3: Configure Google API Credentials in N8N

N8N needs access to Gmail, Drive, and Sheets. Here's how to set it up:

#### 3.1: Open N8N Credentials Page

1. Open `http://localhost:5678`
2. Click **"Settings"** (gear icon) in the sidebar
3. Click **"Credentials"**
4. Click **"Add Credential"**

#### 3.2: Add Gmail Credential

1. Search for **"Gmail OAuth2 API"**
2. Click it
3. You'll need info from your `credentials.json` file

**Open your credentials.json:**
```bash
# Location of your file
C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\credentials.json
```

4. In n8n, fill in:
   - **Client ID**: Copy from `credentials.json` → `installed.client_id`
   - **Client Secret**: Copy from `credentials.json` → `installed.client_secret`

5. Click **"Connect my account"**
6. Authorize in the popup
7. Click **"Save"**
8. Name it: `Google Gmail`

#### 3.3: Add Google Drive Credential

1. Click **"Add Credential"** again
2. Search **"Google Drive OAuth2 API"**
3. Use the **same** Client ID and Secret
4. Connect and authorize
5. Name it: `Google Drive`

#### 3.4: Add Google Sheets Credential

1. Click **"Add Credential"** again
2. Search **"Google Sheets OAuth2 API"**
3. Use the **same** Client ID and Secret
4. Connect and authorize
5. Name it: `Google Sheets`

**✅ Credentials Complete!**

---

### Step 4: Create Your First N8N Workflow

Now we'll create a workflow that uses your Python logic via JavaScript wrappers.

#### 4.1: Create New Workflow

1. Click **"Workflows"** in sidebar
2. Click **"+ Add workflow"**
3. Name it: `Email Processing Workflow`

#### 4.2: Add Webhook Node (Trigger)

1. Click **"Add first step"**
2. Search for **"Webhook"**
3. Click **"Webhook"**

**Configure it:**
- **HTTP Method**: `POST`
- **Path**: `process-emails`
- **Authentication**: `None`
- **Response Mode**: `When Last Node Finishes`
- **Response Data**: `Last Node`

**Important:** After saving, n8n will show you the webhook URL:
```
http://localhost:5678/webhook/process-emails
```

This is the SAME URL your Flask frontend is already configured to use!

4. Click **"Listen for Test Event"** (optional - for testing)
5. Keep this node selected

#### 4.3: Add Code Node (JavaScript)

1. Click the **"+"** button after the Webhook node
2. Search for **"Code"**
3. Click **"Code"**

**Configure it:**
- **Language**: `JavaScript`
- **Mode**: `Run Once for All Items`

**Paste this code:**

```javascript
const { execSync } = require('child_process');
const path = require('path');

// Get input from webhook
const items = $input.all();
const inputData = items[0].json;

// Extract label names
const labelNames = inputData.label_name || inputData.body?.label_name || [];

// Path to Python script
const pythonScriptPath = 'C:\\Users\\dheer\\OneDrive\\Desktop\\projects\\Accrual_Automation_Internal_Trial-main\\n8n_implementation\\webhook_service\\processors\\email_processor.py';

// Build JSON input
const pythonInput = JSON.stringify({
    label_name: labelNames
});

// Execute Python script
try {
    const command = `python "${pythonScriptPath}" "${pythonInput.replace(/"/g, '\\"')}"`;
    const result = execSync(command, { 
        encoding: 'utf-8', 
        maxBuffer: 10 * 1024 * 1024,
        timeout: 300000  // 5 minutes
    });
    
    // Parse result
    const parsedResult = JSON.parse(result);
    
    // Return to n8n
    return [{
        json: parsedResult
    }];
    
} catch (error) {
    // Return error
    return [{
        json: {
            status: 'error',
            message: error.message,
            stderr: error.stderr ? error.stderr.toString() : '',
            stdout: error.stdout ? error.stdout.toString() : ''
        }
    }];
}
```

4. Click **"Execute Node"** to test (if you set up test data)

#### 4.4: Save and Activate Workflow

1. Click **"Save"** button (top right)
2. Toggle the **"Active"** switch to ON
3. Your workflow is now live!

**✅ N8N Workflow Complete!**

---

### Step 5: Update Flask Frontend (If Needed)

Your Flask frontend should already be configured correctly in `.env`:

```bash
# Check your .env file
N8N_WEBHOOK_URL=http://localhost:5678/webhook
```

**If it says something else:**
1. Open `.env` file
2. Make sure `N8N_WEBHOOK_URL=http://localhost:5678/webhook`
3. Save the file
4. Restart Flask frontend

---

### Step 6: Test the Migration

#### 6.1: Test N8N Webhook Directly

**Using curl:**
```bash
curl -X POST http://localhost:5678/webhook/process-emails \
  -H "Content-Type: application/json" \
  -d "{\"label_name\": [\"TestLabel\"]}"
```

**Expected:** You should get a JSON response with processing results.

#### 6.2: Test via Flask Frontend

1. Open `http://localhost:5001`
2. Click **"Process Emails"**
3. Select a test label
4. Click **"Start Processing"**

**Watch N8N:**
- Open n8n UI: `http://localhost:5678`
- Click **"Executions"** in sidebar
- You should see your workflow execution
- Click it to see details

#### 6.3: Verify Results

Check that:
- ✅ Email was processed
- ✅ File uploaded to Google Drive
- ✅ Email moved to "Processed" label
- ✅ No errors in n8n execution

---

### Step 7: Monitor and Debug

#### View N8N Execution Logs

1. Open n8n: `http://localhost:5678`
2. Click **"Executions"** (left sidebar)
3. Click on any execution to see:
   - Input data
   - Output data
   - Errors (if any)
   - Execution time

#### Common Issues and Solutions

**Issue: "Python not found"**
```javascript
// In Code node, use full Python path:
const command = `C:\\Users\\dheer\\AppData\\Local\\Programs\\Python\\Python311\\python.exe "${pythonScriptPath}" "${pythonInput}"`;
```

**Issue: "Module not found"**
- Make sure Python script path is correct
- Check that shared_utils are accessible
- Verify all Python dependencies installed

**Issue: "Timeout"**
- Increase timeout in Code node:
```javascript
timeout: 600000  // 10 minutes
```

**Issue: "JSON parse error"**
- Check Python script output
- Add debugging: `console.log(result)` before parsing

---

### Step 8: Production Checklist

Before using in production:

- [ ] Test with multiple labels
- [ ] Test with large attachments
- [ ] Test error handling (invalid labels, etc.)
- [ ] Set up error notifications (Slack, email, etc.)
- [ ] Document the workflow
- [ ] Create backup of workflow (export JSON)
- [ ] Set up monitoring

---

## 🔄 Rollback Plan

If something goes wrong, you can easily rollback:

### Quick Rollback

1. **Stop n8n:**
   - Press `Ctrl+C` in n8n terminal

2. **Start Python service:**
   ```bash
   cd n8n_implementation/webhook_service
   python app.py
   ```

3. **Done!** System is back to Python mode

---

## 📈 Advanced: Adding More Workflows

Once you're comfortable, you can add more workflows:

### Example: Scheduled Email Processing

1. Create new workflow
2. Add **Cron** node (trigger)
   - Schedule: `0 9 * * *` (daily at 9 AM)
3. Add **Set** node
   - Set `label_name`: `["Label1", "Label2"]`
4. Connect to your Code node (reuse the same code)
5. Activate

### Example: Slack Notifications

1. In your existing workflow
2. Add **Slack** node after Code node
3. Configure to send summary message
4. Connect and activate

---

## 🎓 Learning N8N

To gradually move from Python to native n8n nodes:

### Phase 1: JavaScript Wrappers (Current)
- Uses your Python code
- Works immediately
- Easy to debug

### Phase 2: Hybrid Approach
- Keep complex logic in Python
- Use n8n nodes for simple tasks:
  - Gmail node for fetching emails
  - Drive node for uploads
  - Sheets node for writing

### Phase 3: Full N8N
- Migrate all Python logic to n8n nodes
- Fully visual workflow
- No Python dependencies

**Recommendation:** Stay in Phase 1 for now. It works perfectly and is easier to maintain.

---

## 📞 Support Resources

- **N8N Documentation**: https://docs.n8n.io/
- **N8N Community**: https://community.n8n.io/
- **YouTube Tutorials**: Search "n8n workflow examples"

---

## ✅ Summary

**Current Setup:** ✅ Python webhook service running
**Migration:** Follow steps 1-7 above
**Time Required:** ~30 minutes
**Difficulty:** Medium

**Key Benefits After Migration:**
- ✅ Visual workflow in n8n UI
- ✅ Built-in execution history
- ✅ Easy to add integrations (Slack, etc.)
- ✅ Scheduled workflows
- ✅ Error handling and retries

**Your Python code remains unchanged!** The JavaScript wrapper just calls it.

---

## 🎯 Next Steps

1. ✅ **Complete:** Python service is working
2. **Next:** Follow Step 2 (Start N8N)
3. **Then:** Follow Step 3 (Configure credentials)
4. **Finally:** Follow Step 4 (Create workflow)

**Estimated Time:** 30-45 minutes total

Good luck with your migration! 🚀
