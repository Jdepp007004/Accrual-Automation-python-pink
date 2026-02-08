/**
 * N8N JavaScript Wrapper for Email Processing
 * 
 * This file can be used in an n8n Code node (JavaScript mode).
 * It calls the Python email processor via subprocess and returns results.
 * 
 * HOW TO USE IN N8N:
 * 1. Create a Code node (JavaScript)
 * 2. Copy this entire file into the Code field
 * 3. The node will call the Python script and return results
 */

const { execSync } = require('child_process');
const path = require('path');

// Get input from previous n8n node
const items = $input.all();
const inputData = items[0].json;

// Extract label names from webhook
const labelNames = inputData.label_name || inputData.body?.label_name || [];

// Path to Python script
const pythonScriptPath = path.join(
    'C:',
    'Users',
    'dheer',
    'OneDrive',
    'Desktop',
    'projects',
    'Accrual_Automation_Internal_Trial-main',
    'n8n_implementation',
    'webhook_service',
    'processors',
    'email_processor.py'
);

// Build JSON input for Python script
const pythonInput = JSON.stringify({
    label_name: labelNames
});

// Execute Python script
try {
    const command = `python "${pythonScriptPath}" '${pythonInput.replace(/'/g, "\\'")}'`;
    const result = execSync(command, { encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024 });

    // Parse Python output
    const parsedResult = JSON.parse(result);

    // Return to n8n
    return [{
        json: parsedResult
    }];

} catch (error) {
    // Return error to n8n  
    return [{
        json: {
            status: 'error',
            message: error.message,
            stderr: error.stderr ? error.stderr.toString() : '',
            stdout: error.stdout ? error.stdout.toString() : ''
        }
    }];
}
