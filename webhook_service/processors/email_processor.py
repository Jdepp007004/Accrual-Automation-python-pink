"""
Email Processing Workflow - Main Logic
This is a modular Python function that can be:
1. Called directly by the Python webhook service
2. Called by n8n JavaScript wrapper via subprocess
"""

import os
import sys
import json
import base64
import time
from datetime import datetime
import pytz
import uuid

# Add parent paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared_utils.google_auth import (
    get_google_services, find_or_create_folder, get_label_id,
    find_file_by_name, download_file, upload_or_update_file,
    find_or_create_spreadsheet, create_folder_structure
)
from shared_utils.folder_helpers import create_folder_hierarchy, get_relevant_financial_years
from shared_utils.email_helpers import (
    get_company_info, build_processed_label_name, normalize_name, ensure_label_exists
)
from shared_utils.file_helpers import (
    compute_hash, build_updated_filename, to_float, create_folder_hierarchy
)
from shared_utils.gemini_client import analyze_document_with_gemini
from googleapiclient.http import MediaInMemoryUpload
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(env_path)

# Constants
IST = pytz.timezone('Asia/Kolkata')
ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/webp',
    'application/pdf', 'image/heic', 'image/heif'
}
MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20MB


def load_configurations():
    """Load company aliases and folder structures"""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app')
    
    with open(os.path.join(config_path, 'company_aliases.json')) as f:
        aliases_data = json.load(f)
    
    with open(os.path.join(config_path, 'entity_folder_structures.json')) as f:
        folder_structure_data = json.load(f)
    
    return aliases_data, folder_structure_data


def get_fiscal_year(month: str, year: str, company_name: str, aliases_data: dict) -> str:
    """Calculate fiscal year based on month and company"""
    try:
        month_num = int(month)
        year_num = int(year)
        
        # Get company info to determine fiscal year type
        company_info = get_company_info(aliases_data, company_name)
        fy_type = company_info.get("financial_year", "april-march").lower()
        
        if fy_type == "jan-dec":
            # Calendar year
            return f"{year_num}"
        else:
            # Fiscal year (April-March)
            if month_num >= 4:
                return f"{year_num}-{(year_num + 1) % 100:02d}"
            else:
                return f"{year_num - 1}-{year_num % 100:02d}"
    except:
        return f"{year}-{int(year) + 1}"


def process_emails_workflow(label_names: list, msg_queue=None) -> dict:
    """
    Main email processing workflow.
    This function processes emails for the given Gmail labels.
    
    Args:
        label_names: List of label names to process
        msg_queue: Optional queue for streaming output to browser
        
    Returns:
        Dictionary with processing results
    """
    def emit_log(message, entity=None):
        """Helper to emit log message to both terminal and browser"""
        print(message)
        if msg_queue:
            msg_queue.put({"type": "log", "message": message, "entity": entity})
    
    def emit_header(entity):
        """Helper to emit header update"""
        if msg_queue:
            msg_queue.put({"type": "header", "entity": entity})
    
    # Load configs
    aliases_data, folder_structure_data = load_configurations()
    
    # Get environment variables
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    ROOT_FOLDER_ID = os.getenv('ROOT_FOLDER_ID')
    
    # Get Google services
    gmail, sheets, drive, creds = get_google_services()
    
    # Get all Gmail labels
    all_labels = gmail.users().labels().list(userId="me").execute().get("labels", [])
    label_names_set = {lbl["name"] for lbl in all_labels}
    
    results = []
    now_ist = datetime.now(IST)
    
    for ln in label_names:
        emit_log(f"\n📧 Processing label: {ln}")
        
        # Determine if single or multi-entity
        single_label = f"{ln}/Docs/Repo"
        
        if single_label in label_names_set:
            # Single entity processing
            emit_header(ln)
            result = process_single_entity(
                gmail, sheets, drive, creds, ln, single_label,
                aliases_data, folder_structure_data,
                ROOT_FOLDER_ID, GEMINI_API_KEY, now_ist,
                emit_log=emit_log
            )
            results.append(result)
        else:
            # Multi-entity processing
            entity_labels = [
                lbl["name"] for lbl in all_labels
                if lbl["name"].startswith(f"{ln}/") and lbl["name"].endswith("/Docs/Repo")
            ]
            
            if not entity_labels:
                results.append({
                    "entity": ln,
                    "status": "error",
                    "message": "No valid labels found"
                })
                continue
            
            client_folder_id = find_or_create_folder(drive, ln, ROOT_FOLDER_ID)
            
            for lbl_name in entity_labels:
                entity = lbl_name.split("/")[1]
                emit_header(entity)
                result = process_single_entity(
                    gmail, sheets, drive, creds, entity, lbl_name,
                    aliases_data, folder_structure_data,
                    client_folder_id, GEMINI_API_KEY, now_ist,
                    parent_label_name=ln,
                    emit_log=emit_log
                )
                results.append(result)
    
    return {
        "status": "completed",
        "details": results
    }


def process_single_entity(
    gmail, sheets, drive, creds, entity_name, label_name,
    aliases_data, folder_structure_data,
    parent_folder_id, gemini_api_key, now_ist,
    parent_label_name=None, emit_log=None
):
    """Process emails for a single entity"""
    
    # Default to print if no emit_log provided
    if emit_log is None:
        emit_log = lambda msg, entity=None: print(msg)
    
    emit_log(f"  📁 Processing entity: {entity_name}")
    
    # Get label ID
    label_id = get_label_id(gmail, label_name)
    if not label_id:
        return {
            "entity": entity_name,
            "status": "error",
            "message": f"Label '{label_name}' not found"
        }
    
    # Get company info
    company_info = get_company_info(aliases_data, entity_name)
    entity_type = company_info.get("entity_type", "india")
    
    # Find or create entity folder
    entity_folder_id = find_or_create_folder(drive, entity_name, parent_folder_id)
    
    # Get specific folders we need first
    viable_repo_folder_id = find_or_create_folder(drive, "0. Viable Repo", entity_folder_id)
    docs_repo_id = find_or_create_folder(drive, "0. Docs Repo", viable_repo_folder_id)
    metadata_id = find_or_create_folder(drive, ".metadata", viable_repo_folder_id)
    
    # Create complete folder structure from JSON
    emit_log(f"  📁 Creating complete folder structure...")
    try:
        # Load the full entity structure from JSON
        entity_structure = folder_structure_data.get(entity_type, folder_structure_data.get("india", {}))
        
        # Create all folders from JSON (this includes all sections like Company Docs, Financial Docs, etc.)
        create_folder_hierarchy(drive, entity_folder_id, entity_structure)
        
        # Also create financial year folders for past 2, current, and next 1 years
        relevant_fys = get_relevant_financial_years()
        for fy_year in relevant_fys:
            try:
                create_folder_structure(drive, fy_year, entity_folder_id, entity_type, company_info.get("name", entity_name))
                emit_log(f"    ✅ Created FY {fy_year} folder structure")
            except Exception as e:
                emit_log(f"    ⚠️  Warning: Could not create FY {fy_year} structure: {str(e)}")
    except Exception as e:
        emit_log(f"  ⚠️  Warning: Could not create full folder structure: {str(e)}")
    
    # Create or find spreadsheet with updated signature
    spreadsheet_name = f"{entity_name} Workbook"
    sheet_tab_names = ["Docs Extraction", "Inflow", "Outflow", "Others"]
    
    emit_log(f"  📊 Setting up spreadsheet: {spreadsheet_name}")
    spreadsheet_id = find_or_create_spreadsheet(
        drive, sheets, spreadsheet_name, viable_repo_folder_id,
        creds, sheet_tab_names, entity_type, company_info.get("name", entity_name)
    )
    
    # Fetch existing file links from "Docs Extraction" sheet for duplicate checking
    emit_log(f"  🔍 Checking for existing files in spreadsheet...")
    existing_files = set()
    try:
        range_name = "Docs Extraction!H:H"  # File Link column (column H = index 8)
        result = sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])
        
        # Extract file links (skip header row)
        for row in values[1:]:
            if row and row[0]:
                file_link = row[0]
                existing_files.add(file_link)
    except Exception as e:
        emit_log(f"  ⚠️  Could not fetch existing files: {str(e)}")
    
    emit_log(f"  📋 Found {len(existing_files)} existing files in 'Docs Extraction' sheet")
    
    # Get processed label ID
    if parent_label_name:
        processed_label_id = build_processed_label_name(gmail, parent_label_name, entity_name)
    else:
        processed_label_id = build_processed_label_name(gmail, entity_name)
    
    # Fetch emails
    threads_response = gmail.users().threads().list(userId="me", labelIds=[label_id]).execute()
    threads = threads_response.get("threads", [])
    
    emit_log(f"  📨 Found {len(threads)} thread(s)")
    
    threads_processed = 0
    attachments_added = 0
    skipped_files = []
    
    for thread in threads:
        thread_id = thread['id']
        thread_data = gmail.users().threads().get(userId="me", id=thread_id, format="full").execute()
        messages = thread_data.get("messages", [])
        
        for msg_data in messages:
            msg_id = msg_data['id']
            
            # Skip if already processed
            if processed_label_id in msg_data.get("labelIds", []):
                continue
            
            # Skip if doesn't have the trigger label
            if label_id not in msg_data.get("labelIds", []):
                continue
            
            payload = msg_data.get("payload", {})
            headers = payload.get("headers", [])
            
            # Extract email metadata
            email_from = ""
            email_subject = ""
            for h in headers:
                if h["name"].lower() == "from":
                    email_from = h["value"]
                elif h["name"].lower() == "subject":
                    email_subject = h["value"]
            
            # Get email link
            email_link = f"https://mail.google.com/mail/u/0/#all/{msg_id}"
            
            # Date of extraction
            date_of_extraction = now_ist.strftime('%Y-%m-%d %H:%M:%S')
            
            parts = payload.get("parts", [])
            
            for part in parts:
                filename = part.get("filename")
                mime_type = part.get("mimeType")
                att_id = part.get("body", {}).get("attachmentId")
                
                if not filename or not att_id:
                    continue
                
                if mime_type not in ALLOWED_MIME_TYPES:
                    skipped_files.append({
                        "filename": filename,
                        "reason": f"Unsupported type: {mime_type}"
                    })
                    continue
                
                # Download attachment
                try:
                    att = gmail.users().messages().attachments().get(
                        userId="me", messageId=msg_id, id=att_id
                    ).execute()
                    file_data = base64.urlsafe_b64decode(att['data'].encode('UTF-8'))
                except Exception as e:
                    skipped_files.append({
                        "filename": filename,
                        "reason": f"Download failed: {str(e)}"
                    })
                    continue
                
                # Check size
                if len(file_data) > MAX_SIZE_BYTES:
                    skipped_files.append({
                        "filename": filename,
                        "reason": "File too large"
                    })
                    continue
                
                # Check duplicates against spreadsheet
                # We'll check after upload since we need the Drive link
                
                # Analyze with Gemini
                emit_log(f"    🤖 Analyzing: {filename}")
                time.sleep(5)  # Rate limiting
                
                try:
                    documents = analyze_document_with_gemini(
                        file_data, mime_type, gemini_api_key
                    )
                    emit_log(f"    📄 Gemini returned {len(documents)} document(s)")
                except Exception as e:
                    emit_log(f"    ❌ Gemini analysis failed: {str(e)}")
                    skipped_files.append({
                        "filename": filename,
                        "reason": f"Gemini analysis failed: {str(e)}"
                    })
                    continue
                
                if not documents:
                    emit_log(f"    ⚠️  No documents extracted from {filename}")
                    continue
                
                # Process each document
                for doc in documents:
                    # Determine entity for filename
                    seller_name = normalize_name(doc.get("Seller Name", ""))
                    buyer_name = doc.get("Buyer Name", "")
                    company_names = [normalize_name(company_info.get("name", entity_name))] + \
                                    [normalize_name(alias) for alias in company_info.get("aliases", [])]
                    
                    entity_for_filename = doc.get("Seller Name", "")
                    if seller_name in company_names:
                        entity_for_filename = buyer_name
                    
                    # Build filename
                    updated_filename = build_updated_filename(doc, entity_for_filename)
                    ext = os.path.splitext(filename)[-1]
                    updated_filename_with_ext = f"{updated_filename}{ext}"
                    
                    # Upload to Drive
                    emit_log(f"    ☁️  Uploading: {updated_filename_with_ext}")
                    try:
                        media = MediaInMemoryUpload(file_data, mimetype=mime_type, resumable=True)
                        file_metadata = {
                            'name': updated_filename_with_ext,
                            'parents': [docs_repo_id]
                        }
                        uploaded = drive.files().create(
                            body=file_metadata,
                            media_body=media,
                            fields='id, webViewLink',
                            supportsAllDrives=True
                        ).execute()
                        
                        file_link = uploaded.get('webViewLink')
                        
                        # Check if this file link already exists in the sheet
                        if file_link in existing_files:
                            emit_log(f"    ⚠️  Skipping duplicate (already in sheet): {updated_filename_with_ext}")
                            # Delete the uploaded file
                            drive.files().delete(fileId=uploaded['id'], supportsAllDrives=True).execute()
                            continue
                        
                        emit_log(f"    ✅ Uploaded: {file_link}")
                        attachments_added += 1
                        
                        # Determine Flow based on company name match
                        seller = normalize_name(doc.get("Seller Name", ""))
                        flow = "Inflow" if seller in company_names else "Outflow"
                        
                        # Name selection logic (matching main app)
                        row_buyer_name = doc.get("Buyer Name", "")
                        row_seller_name = doc.get("Seller Name", "")
                        
                        if flow == "Inflow":
                            # We are Seller
                            row_seller_name = company_info.get("name", entity_name)
                            if entity_type == "us":
                                row_buyer_name = entity_for_filename
                        else:
                            # We are Buyer (Outflow)
                            row_buyer_name = company_info.get("name", entity_name)
                            if entity_type == "us":
                                row_seller_name = entity_for_filename
                        
                        # GSTIN & PAN selection (counterparty only)
                        gstin_val = ""
                        pan_val = ""
                        
                        if flow == "Inflow":
                            gstin_val = doc.get("Buyer GSTIN") or doc.get("GSTIN", "")
                            pan_val = doc.get("Buyer PAN") or doc.get("PAN", "")
                        else:
                            gstin_val = doc.get("Seller GSTIN") or doc.get("GSTIN", "")
                            pan_val = doc.get("Seller PAN") or doc.get("PAN", "")
                        
                        # Capitalize
                        if gstin_val: gstin_val = str(gstin_val).upper().strip()
                        if pan_val: pan_val = str(pan_val).upper().strip()
                        
                        # Date formatting
                        invoice_date_str = doc.get("Invoice Date", "")
                        formatted_date_for_sheet = invoice_date_str
                        try:
                            if invoice_date_str:
                                # Start format: DD Mon YYYY (from Gemini rules)
                                dt_obj = datetime.strptime(invoice_date_str.strip(), "%d %b %Y")
                                formatted_date_for_sheet = dt_obj.strftime("%Y-%m-%d")
                        except Exception:
                            # Fallback to original string if parse fails
                            pass
                        
                        # Other fields & unique ID
                        invoice_month = doc.get("Invoice Month", "")
                        invoice_year = doc.get("Invoice Year", "")
                        financial_year = get_fiscal_year(invoice_month, invoice_year, entity_name, aliases_data)
                        client_unique_id = f"{entity_name} / {financial_year} / {str(uuid.uuid4().int)[:6]}"
                        
                        hsn_sac = doc.get("HSN/SAC", "")
                        if isinstance(hsn_sac, list): hsn_sac = ", ".join(hsn_sac)
                        gst_percentage = doc.get("GST Percentage", "")
                        if isinstance(gst_percentage, list): gst_percentage = ", ".join(gst_percentage)
                        
                        # Helper function to convert to float
                        def to_float(val):
                            if val == "" or val is None:
                                return ""
                            try:
                                return float(val)
                            except:
                                return val
                        
                        # Build row with exact same structure as main app
                        row_data = [
                            client_unique_id, 
                            email_from, 
                            email_subject, 
                            date_of_extraction,
                            filename, 
                            updated_filename_with_ext,
                            email_link, 
                            file_link,
                            "",  # Duplicates Column
                            row_buyer_name, 
                            row_seller_name,
                            doc.get("Doc Number", ""), 
                            formatted_date_for_sheet,
                            doc.get("Invoice Month Name", ""), 
                            financial_year,
                            doc.get("Currency", ""),
                            to_float(doc.get("Total Amount", "")),
                            to_float(doc.get("Gross Amount", "")),
                            to_float(doc.get("GST", "")),
                            to_float(doc.get("TDS", "")),
                            to_float(doc.get("Other Taxes", "")),
                            to_float(doc.get("Net Amount", "")),
                            to_float(doc.get("CGST", "")),
                            to_float(doc.get("SGST", "")),
                            to_float(doc.get("IGST", "")),
                            gst_percentage, 
                            doc.get("Seller State", ""), 
                            hsn_sac,
                            gstin_val, 
                            pan_val, 
                            flow,
                        ]
                        
                        # Add row to "Docs Extraction" sheet
                        try:
                            sheets.spreadsheets().values().append(
                                spreadsheetId=spreadsheet_id,
                                range="Docs Extraction!A:Z",
                                valueInputOption="USER_ENTERED",
                                body={"values": [row_data]}
                            ).execute()
                            emit_log(f"    ➕ Added row to spreadsheet for {updated_filename_with_ext}")
                            existing_files.add(file_link) # Add to set for future duplicate checks
                        except Exception as e:
                            emit_log(f"    ⚠️  Failed to add row to spreadsheet: {str(e)}")
                        
                    except Exception as e:
                        emit_log(f"    ❌ Upload failed for {filename}: {str(e)}")
                        skipped_files.append({
                            "filename": filename,
                            "reason": f"Upload failed: {str(e)}"
                        })
                        continue
            
            # Modify labels
            try:
                gmail.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={
                        'addLabelIds': [processed_label_id],
                        'removeLabelIds': [label_id]
                    }
                ).execute()
            except Exception as e:
                emit_log(f"    ⚠️  Failed to modify labels: {str(e)}")
        
        threads_processed += 1
    
    emit_log(f"  ✅ Processed {threads_processed} threads, {attachments_added} attachments")
    
    return {
        "entity": entity_name,
        "status": "success",
        "threads_processed": threads_processed,
        "attachments_added": attachments_added,
        "skipped_files": skipped_files
    }


# For testing standalone
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Called from command line with JSON input
        input_json = sys.argv[1]
        data = json.loads(input_json)
        label_names = data.get('label_name', [])
        result = process_emails_workflow(label_names)
        print(json.dumps(result, indent=2))
    else:
        # Test with hardcoded label
        result = process_emails_workflow(["TestLabel"])
        print(json.dumps(result, indent=2))
