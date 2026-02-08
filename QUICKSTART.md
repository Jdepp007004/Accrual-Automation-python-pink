# ⚡ Quick Start - Single Command

**Already set up?** Just run this:

```powershell
cd C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation
python run.py
```

**Then open:** http://localhost:5001

---

## 🆕 First Time Setup?

Follow these steps:

### 1. Complete Setup (One Time Only)
See [SETUP.md](SETUP.md) for detailed instructions:
- Google Cloud Console setup
- Enable Gmail & Drive APIs
- Get Gemini API key
- Configure `.env` file

### 2. Install Dependencies
```powershell
cd C:\Users\dheer\OneDrive\Desktop\projects\Accrual_Automation_Internal_Trial-main\n8n_implementation
pip install -r requirements.txt
```

### 3. Run the Application
```powershell
python run.py
```

---

## 📖 Documentation

- **[SETUP.md](SETUP.md)** - Complete setup guide from scratch
- **[RUN_GUIDE.md](RUN_GUIDE.md)** - Detailed usage instructions and troubleshooting

---

## 🎯 What This Does

1. **Monitors Gmail** labels for incoming emails with attachments
2. **Analyzes documents** using Google Gemini AI to extract metadata
3. **Renames files** with structured naming (Date_Company_Currency_Amount)
4. **Uploads to Google Drive** in organized folder structures
5. **Updates Gmail labels** to mark emails as processed

All from a beautiful web interface! 🚀
