# 🛠️ Complete Setup Guide - Windows System

This guide will walk you through setting up the Accrual Automation system on your Windows machine from scratch.

---

## 📋 Prerequisites

- **Python 3.8+** installed on your system
- **Google Account** with Gmail and Google Drive access
- **Internet connection**

---

## 🔧 Step 1: Google Cloud Console Setup

### 1.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project name: `Accrual Automation`
4. Click **"Create"**

### 1.2 Enable Required APIs

1. In the search bar, type **"Gmail API"** → Click it → Click **"Enable"**
2. In the search bar, type **"Google Drive API"** → Click it → Click **"Enable"**
3. In the search bar, type **"Google Sheets API"** → Click it → Click **"Enable"**

### 1.3 Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. If prompted to configure OAuth consent screen:
   - Select **"External"** → Click **"Create"**
   - App name: `Accrual Automation`
   - User support email: Your email
   - Developer contact: Your email
   - Click **"Save and Continue"** through all steps
   - Add your email as a test user
4. Back to Create OAuth client ID:
   - Application type: **"Desktop app"**
   - Name: `Accrual Automation Desktop`
   - Click **"Create"**
5. Click **"Download JSON"** (downloads as `client_secret_...json`)
6. **Rename this file to `credentials.json`**
7. **Move it to:** `C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\credentials.json`

---

## 🔑 Step 2: Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click **"Create API Key"**
3. Select your Google Cloud project or create new one
4. Copy the API key (you'll need this for `.env` file)

---

## 📁 Step 3: Get Google Drive Root Folder ID

1. Open Google Drive in your browser
2. Navigate to (or create) the folder where you want files uploaded
3. Click on the folder to open it
4. Look at the URL in your browser:
   ```
   https://drive.google.com/drive/folders/1ABC...XYZ123
   ```
5. Copy everything after `/folders/` - this is your **ROOT_FOLDER_ID**

---

## ⚙️ Step 4: Configure Environment Variables

1. Navigate to the project directory:
   ```powershell
   cd C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation
   ```

2. Copy the example environment file:
   ```powershell
   copy .env.example .env
   ```

3. Open `.env` in your text editor (Notepad, VS Code, etc.)

4. Fill in your values:
   ```env
   FLASK_SECRET_KEY=my-super-secret-key-12345
   FLASK_PORT=5001
   ROOT_FOLDER_ID=paste-your-folder-id-here
   GEMINI_API_KEY=paste-your-gemini-api-key-here
   ```

5. Save the file

---

## 📦 Step 5: Install Python Dependencies

1. Open **PowerShell** or **Command Prompt**

2. Navigate to the project:
   ```powershell
   cd C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation
   ```

3. **(Optional but Recommended)** Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   
   If you get an execution policy error:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

---

## ✅ Step 6: First-Time Authentication

1. Run the application for the first time:
   ```powershell
   python run.py
   ```

2. A browser window will automatically open asking you to:
   - Sign in to your Google Account
   - Grant permissions to access Gmail, Drive, and Sheets
   - Click **"Allow"**

3. A `token.json` file will be created in the parent directory
   - This stores your authentication credentials
   - You won't need to authenticate again unless you delete this file

4. The application should now be running!

---

## 🎯 Step 7: Verify Everything Works

### Test 1: Open the Dashboard
1. Open browser to: http://localhost:5001
2. You should see the beautiful dashboard UI

### Test 2: Check Gmail Labels
1. Click **"Process Emails"**
2. You should see a list of your Gmail labels
3. If labels show up, Gmail API is working! ✅

### Test 3: Test Health Endpoint
```powershell
curl http://localhost:5001/health
```
Should return:
```json
{
  "status": "healthy",
  "service": "accrual-automation-unified",
  "version": "2.0"
}
```

---

## 📂 File Structure Overview

After setup, your structure should look like:

```
Accrual_Automation_Internal_Trial-main/
├── credentials.json          👈 Google OAuth credentials
├── token.json               👈 Generated on first auth (auto-created)
├── app/
│   ├── company_aliases.json
│   └── entity_folder_structures.json
└── n8n_implementation/
    ├── run.py               👈 Main file - run this!
    ├── requirements.txt
    ├── .env                 👈 Your configuration
    ├── shared_utils/
    ├── flask_frontend/
    └── webhook_service/
```

---

## 🚨 Troubleshooting

### "credentials.json not found"
- Make sure `credentials.json` is in the parent directory
- Correct path: `C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\credentials.json`

### "ModuleNotFoundError"
```powershell
pip install -r requirements.txt
```

### "Permission denied" when creating venv
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Google Auth keeps asking for permissions
- Delete `token.json`
- Run `python run.py` again to re-authenticate

### "No such file or directory" errors
- Make sure you're in the correct directory:
  ```powershell
  cd C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation
  ```

---

## 🎉 You're All Set!

Now you can run the application anytime with:

```powershell
cd C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation
python run.py
```

Then open: **http://localhost:5001**

See [RUN_GUIDE.md](RUN_GUIDE.md) for usage instructions.
