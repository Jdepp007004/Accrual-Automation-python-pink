# N8N JavaScript Wrappers

These JavaScript files are designed to be used in **n8n Code nodes** to call the Python processors.

## How It Works

1. **NOW**: Run the Python webhook service directly (`webhook_service/app.py`)
2. **LATER**: Import n8n workflow and use these JS wrappers in Code nodes

## Architecture

```
N8N Workflow
    ↓
Code Node (JavaScript)
    ↓
Executes Python Script via subprocess
    ↓
Python script processes data
    ↓
Returns JSON result
    ↓
N8N continues workflow
```

## Benefits

- ✅ **Python logic remains unchanged** - All business logic stays in Python
- ✅ **Easy migration** - JavaScript is just a thin wrapper
- ✅ **Testable** - Python scripts can be tested standalone
- ✅ **Maintainable** - Update Python, JS wrapper stays the same

## Available Wrappers

### 1. `process_emails_wrapper.js`

Calls the main email processing workflow.

**Usage in N8N:**
1. Create a **Code** node (JavaScript)
2. Copy the contents of `process_emails_wrapper.js`
3. Connect to Webhook node

**Input:** Expects `label_name` array from previous node
**Output:** Processing results with status and details

## Example N8N Workflow

```
[Webhook] → [Code: Process Emails] → [Set Response]
```

1. **Webhook Node:**
   - Path: `process-emails`
   - Method: POST

2. **Code Node (JavaScript):**
   - Paste `process_emails_wrapper.js` content
   - Calls Python processor
   - Returns results

3. **Set Response Node:**
   - Formats output for webhook response

## Migration Path

### Phase 1: Python Service (NOW)
```
Flask Frontend → Python Webhook Service → Google APIs
                 (port 5678)
```

### Phase 2: N8N Visual (LATER)
```
Flask Frontend → N8N Webhook → Code Node (JS) → Python Script → Google APIs
```

### Phase 3: Full N8N (FUTURE)
```
Flask Frontend → N8N Workflow → Native N8N Nodes → Google APIs
                                (Gmail, Drive, Sheets)
```

## Testing the Wrapper

You can test the JavaScript wrapper in n8n:

1. Start n8n: (if not running)
2. Import a test workflow
3. Add Webhook + Code node
4. Paste the JS wrapper code
5. Execute with test data

## Troubleshooting

**Error: "python not found"**
- Ensure Python is in PATH
- Or use full path to python.exe in the JS wrapper

**Error: "Module not found"**
- Check Python script path in the JS file
- Ensure all Python dependencies are installed

**Error: "JSON parse error"**
- Check Python script output format
- Ensure it returns valid JSON

## File Structure

```
n8n_js_wrappers/
├── process_emails_wrapper.js  # Main email processing
├── README.md                   # This file
└── (future wrappers)           # Additional processors
```

## Adding New Wrappers

To create a new wrapper for a different operation:

1. Create Python script in `webhook_service/processors/`
2. Make it accept JSON input and return JSON output
3. Create JS wrapper in this directory
4. Use same pattern as `process_emails_wrapper.js`

---

**Current Status:** Python webhook service is fully functional. JavaScript wrappers are ready for n8n migration when needed.
