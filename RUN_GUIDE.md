# 🚀 Run Guide - Single Command Execution

## ⚡ Quick Start

**You only need ONE terminal!** No more juggling multiple servers.

### Step 1: Navigate to Project Directory

```powershell
cd C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation
```

### Step 2: Install Dependencies (First Time Only)

```powershell
pip install -r requirements.txt
```

### Step 3: Run the Application

```powershell
python run.py
```

**✅ Success looks like:**
```
============================================================
🚀 Accrual Automation - Unified Python Implementation
============================================================
✨ Starting on: http://localhost:5001
📁 Working directory: C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation
🔧 Environment loaded from: C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation\.env
============================================================
📋 Available endpoints:
   • Dashboard: http://localhost:5001/
   • Process Emails: http://localhost:5001/process-emails
   • Manage Companies: http://localhost:5001/manage-companies
   • Health Check: http://localhost:5001/health
============================================================
✅ Ready! Open your browser to get started.
💡 Press Ctrl+C to stop the server
============================================================

 * Running on http://127.0.0.1:5001
```

---

## 🌐 Use the Application

### Step 1: Open Your Browser

Go to: **http://localhost:5001**

You should see a beautiful purple/blue gradient dashboard.

### Step 2: Process Emails

1. Click **"Process Emails"** in the navigation
2. You'll see a list of your Gmail labels
3. Select one or more labels (e.g., "TestLabel")
4. Click **"Start Processing"**

### Step 3: Watch It Work

In your **terminal**, you'll see live processing output:
```
📧 Processing label: TestLabel
  📁 Processing entity: TestLabel
  📨 Found 3 thread(s)
    🤖 Analyzing: invoice.pdf
    ☁️  Uploading: 2024-01-15_CompanyName_USD_1000.pdf
    ✅ Uploaded: https://drive.google.com/...
  ✅ Processed 3 threads, 3 attachments
```

In your **browser**, you'll see the results displayed when complete.

---

## ✅ Verify Results

### Check Gmail
- Open Gmail
- Your processed emails should be moved to "Processed" label

### Check Google Drive
- Open Google Drive
- Navigate to your root folder → Company Name → "0. Viable Repo" → "0. Docs Repo"
- Files should be there with renamed filenames

---

## 🛑 Stop the Application

When you're done:

Press **`Ctrl+C`** in the terminal

---

## 🔄 Restart Anytime

Just run `python run.py` again!

---

## 🧪 Testing

### Test Health Check
```powershell
curl http://localhost:5001/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "accrual-automation-unified",
  "version": "2.0"
}
```

### Test Labels API
```powershell
curl http://localhost:5001/api/labels
```

---

## ⚠️ Common Issues

### "Port 5001 already in use"
**Solution:** Change `FLASK_PORT` in `.env` file to a different port (e.g., 5002)

### "Module not found" 
**Solution:** 
```powershell
pip install -r requirements.txt
```
Make sure you're in the correct directory.

### "Google Auth Error"
**Solution:** 
1. Check that `credentials.json` exists in parent directory
2. Delete `token.json` and run the app again to re-authenticate
3. Or run the auth test:
```powershell
python C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\test_auth.py
```

### "No labels showing up"
**Solution:**
- Check that `credentials.json` and `token.json` exist in the parent directory
- Verify Google APIs are enabled (see SETUP.md)
- Try refreshing the page

### "ROOT_FOLDER_ID not found"
**Solution:**
- Make sure you've set `ROOT_FOLDER_ID` in your `.env` file
- Get the folder ID from your Google Drive folder URL

---

## 📁 Project Structure

```
n8n_implementation/
├── run.py                    👈 Main entry point (run this!)
├── requirements.txt          👈 All dependencies
├── .env                      👈 Your configuration
├── shared_utils/             👈 Shared utilities
├── flask_frontend/           
│   ├── templates/            👈 HTML templates
│   └── static/               👈 CSS, JS, images
└── webhook_service/
    └── processors/           👈 Email processing logic
```

---

## 🎯 That's It!

**One command to rule them all:**

```powershell
cd C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation
python run.py
```

**Then open:** http://localhost:5001

**Enjoy! 🚀**
