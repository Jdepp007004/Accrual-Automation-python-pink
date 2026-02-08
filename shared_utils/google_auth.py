"""
Google API authentication and helper functions for N8N workflows.
These functions provide Google service initialization and common API operations.
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# If modifying these scopes, delete the token.json file
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/script.projects',
    'https://www.googleapis.com/auth/script.external_request'
]


def get_google_services(credentials_path: str = None, token_path: str = None):
    """
    Authenticate with Google APIs and return service objects.
    
    Args:
        credentials_path: Path to credentials.json file
        token_path: Path to token.json file
        
    Returns:
        Tuple of (gmail, sheets, drive, credentials)
    """
    if not credentials_path:
        # Default to n8n_implementation directory
        credentials_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
    
    if not token_path:
        # Default to n8n_implementation directory
        token_path = os.path.join(os.path.dirname(__file__), '..', 'token.json')
    
    creds = None
    
    # Load existing token if available
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    # Build service objects
    gmail = build('gmail', 'v1', credentials=creds)
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)
    
    return gmail, sheets, drive, creds


def find_or_create_folder(drive, folder_name: str, parent_id: str) -> str:
    """
    Find or create a Google Drive folder.
    
    Args:
        drive: Google Drive API service object
        folder_name: Name of the folder
        parent_id: Parent folder ID
        
    Returns:
        Folder ID
    """
    query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    
    results = drive.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    
    # Create folder if not exists
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    
    folder = drive.files().create(
        body=file_metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()
    
    return folder['id']


def find_file_by_name(drive, file_name: str, parent_id: str = None):
    """
    Find a file by name in Google Drive.
    
    Args:
        drive: Google Drive API service object
        file_name: Name of the file to find
        parent_id: Optional parent folder ID to search within
        
    Returns:
        File metadata dict if found, None otherwise
    """
    query = f"name='{file_name}' and trashed=false"
    
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = drive.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType)',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    items = results.get('files', [])
    return items[0] if items else None


def download_file(drive, file_id: str) -> str:
    """
    Download a file from Google Drive.
    
    Args:
        drive: Google Drive API service object
        file_id: ID of the file to download
        
    Returns:
        File content as string
    """
    request = drive.files().get_media(fileId=file_id)
    content = request.execute()
    
    if isinstance(content, bytes):
        return content.decode('utf-8')
    return content


def upload_or_update_file(drive, parent_id: str, file_name: str, content: str):
    """
    Upload or update a file in Google Drive.
    
    Args:
        drive: Google Drive API service object
        parent_id: Parent folder ID
        file_name: Name of the file
        content: File content as string
    """
    from googleapiclient.http import MediaInMemoryUpload
    
    existing_file = find_file_by_name(drive, file_name, parent_id)
    
    media = MediaInMemoryUpload(
        content.encode('utf-8'),
        mimetype='application/json',
        resumable=True
    )
    
    if existing_file:
        # Update existing file
        drive.files().update(
            fileId=existing_file['id'],
            media_body=media,
            supportsAllDrives=True
        ).execute()
    else:
        # Create new file
        file_metadata = {
            'name': file_name,
            'parents': [parent_id]
        }
        drive.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()


def get_label_id(gmail, label_name: str) -> str:
    """
    Get Gmail label ID by name.
    
    Args:
        gmail: Gmail API service object
        label_name: Name of the label
        
    Returns:
        Label ID or None if not found
    """
    all_labels = gmail.users().labels().list(userId="me").execute().get("labels", [])
    
    for lbl in all_labels:
        if lbl["name"] == label_name:
            return lbl["id"]
    return None


def find_or_create_spreadsheet(drive, sheets, name: str, parent_id: str, creds, sheet_tab_names: list, entity_type: str, company_name: str = None) -> str:
    """
    Find or create a Google Spreadsheet in the specified folder.
    
    Args:
        drive: Google Drive API service object
        sheets: Google Sheets API service object
        name: Name of the spreadsheet
        parent_id: Parent folder ID
        creds: Google API credentials object
        sheet_tab_names: List of sheet tab names to create
        entity_type: Type of entity ('india' or 'us')
        company_name: Optional company name for customization
        
    Returns:
        Spreadsheet ID
    """
    from .config import DOCS_EXTRACTION_HEADERS, INFLOW_OUTFLOW_OTHERS_HEADERS
    
    # Check if spreadsheet already exists
    query = f"'{parent_id}' in parents and name='{name}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    
    results = drive.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    files = results.get("files", [])
    
    if files:
        # Spreadsheet exists, ensure all tabs exist
        spreadsheet_id = files[0]["id"]
        spreadsheet = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
        
        requests = []
        for sheet_name in sheet_tab_names:
            if sheet_name not in existing_sheets:
                requests.append({'addSheet': {'properties': {'title': sheet_name}}})
        
        if requests:
            body = {'requests': requests}
            sheets.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
        
        return spreadsheet_id
    
    # Create new spreadsheet
    spreadsheet = {
        "properties": {"title": name},
        "sheets": [{"properties": {"title": name}} for name in sheet_tab_names]
    }
    
    sheet_file = sheets.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
    file_id = sheet_file["spreadsheetId"]
    
    # Move to correct folder
    drive.files().update(
        fileId=file_id,
        addParents=parent_id,
        fields="id, parents",
        supportsAllDrives=True
    ).execute()
    
    # Add headers to each sheet
    for sheet_name in sheet_tab_names:
        headers_to_use = INFLOW_OUTFLOW_OTHERS_HEADERS
        if "extraction" in sheet_name.lower():
            headers_to_use = DOCS_EXTRACTION_HEADERS
        
        sheets.spreadsheets().values().update(
            spreadsheetId=file_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": [headers_to_use]}
        ).execute()
    
    # Attach Apps Script for validation and dropdowns
    attach_script_to_sheet(file_id, creds, entity_type, company_name)
    
    return file_id



def get_financial_docs_structure(entity_type: str, company_name: str = None) -> dict:
    """
    Get the financial year folder structure based on entity type and company name.
    Supports numbered months (e.g., '1.Apr', '2.May') and Riffle Inc calendar year logic.
    
    Args:
        entity_type: Type of entity ('india' or 'us')
        company_name: Company name to determine fiscal year type
        
    Returns:
        Dictionary representing folder structure
    """
    # Determine Month Keys based on Company Name
    if company_name and "riffle inc" in company_name.lower():
        # Calendar Year: 1.Jan - 12.Dec
        months = {
             "1.Jan": {"Inflow": {}, "Outflow": {}},
             "2.Feb": {"Inflow": {}, "Outflow": {}},
             "3.Mar": {"Inflow": {}, "Outflow": {}},
             "4.Apr": {"Inflow": {}, "Outflow": {}},
             "5.May": {"Inflow": {}, "Outflow": {}},
             "6.Jun": {"Inflow": {}, "Outflow": {}},
             "7.Jul": {"Inflow": {}, "Outflow": {}},
             "8.Aug": {"Inflow": {}, "Outflow": {}},
             "9.Sep": {"Inflow": {}, "Outflow": {}},
             "10.Oct": {"Inflow": {}, "Outflow": {}},
             "11.Nov": {"Inflow": {}, "Outflow": {}},
             "12.Dec": {"Inflow": {}, "Outflow": {}}
        }
    else:
        # Fiscal Year: 1.Apr - 12.Mar (Default)
        months = {
             "1.Apr": {"Inflow": {}, "Outflow": {}},
             "2.May": {"Inflow": {}, "Outflow": {}},
             "3.Jun": {"Inflow": {}, "Outflow": {}},
             "4.Jul": {"Inflow": {}, "Outflow": {}},
             "5.Aug": {"Inflow": {}, "Outflow": {}},
             "6.Sep": {"Inflow": {}, "Outflow": {}},
             "7.Oct": {"Inflow": {}, "Outflow": {}},
             "8.Nov": {"Inflow": {}, "Outflow": {}},
             "9.Dec": {"Inflow": {}, "Outflow": {}},
             "10.Jan": {"Inflow": {}, "Outflow": {}},
             "11.Feb": {"Inflow": {}, "Outflow": {}},
             "12.Mar": {"Inflow": {}, "Outflow": {}}
        }

    if entity_type == 'india':
        return {
            "1. IN_Income Tax": {"0. Docs Repo": {}},
            "2. IN_TDS-TCS": {"0. Docs Repo": {}},
            "3. IN_GST": {"0. Docs Repo": {}},
            "4. IN_Payroll-Labour": {"0. Docs Repo": {}},
            "5. IN_Financials-Audit": {"0. Docs Repo": {}},
            "6. IN_Banking-Treasury": {"0. Docs Repo": {}},
            "7. IN_Invoices & Bills": {
                "0. Docs Repo": {},
                **months
            },
            "8. IN_Reports": {"0. Docs Repo": {}},
            "9. IN_Ops Docs": {"0. Docs Repo": {}},
            "10. IN_Others": {"0. Docs Repo": {}}
        }
    else:  # Default to US structure
        return {
            "1. US_Financial Reports": {"0. Docs Repo": {}},
            "2. US_Compliances & Legal": {"0. Docs Repo": {}},
            "3. US_Invoices & Bills": {
                "0. Docs Repo": {},
                **months
            }
        }


def create_folder_structure(drive, financial_year: str, parent_id: str, entity_type: str, company_name: str = None):
    """
    Creates the folder structure for a given financial year if it doesn't exist.
    
    Args:
        drive: Google Drive API service object
        financial_year: Financial year string (e.g., '2025-2026')
        parent_id: Parent folder ID (entity root)
        entity_type: Type of entity ('india' or 'us')
        company_name: Optional company name for customization
    """
    # Find or create "Financial Related Docs (Accounting, Audit & Taxation)"
    financial_docs_folder_id = find_or_create_folder(
        drive,
        "2. Financial Related Docs (Accounting, Audit & Taxation)" if entity_type == "india" else "2. Financial Related Docs",
        parent_id
    )

    # Find or create "FY ${Invoice Financial Year}"
    fy_folder_id = find_or_create_folder(drive, f"FY {financial_year}", financial_docs_folder_id)

    # Create the subfolders
    subfolders_structure = get_financial_docs_structure(entity_type, company_name)
    
    # Import create_folder_hierarchy
    from .folder_helpers import create_folder_hierarchy
    create_folder_hierarchy(drive, fy_folder_id, subfolders_structure)
            
    return fy_folder_id


def attach_script_to_sheet(file_id: str, creds, entity_type: str, company_name: str = None):
    """
    Attaches an Apps Script to the spreadsheet for validation and dropdowns.
    
    Args:
        file_id: Spreadsheet file ID
        creds: Google API credentials
        entity_type: Type of entity ('india' or 'us')
        company_name: Optional company name for customization
    """
    from googleapiclient.discovery import build
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    script_service = build("script", "v1", credentials=creds)
    drive_svc = build("drive", "v3", credentials=creds)
    
    # Step 1: Create a new Apps Script project bound to the spreadsheet
    request = {
        "title": "SheetValidationScript",
        "parentId": file_id
    }
    response = script_service.projects().create(body=request).execute()
    script_id = response["scriptId"]
    
    # Determine CURRENT Financial Year
    from .folder_helpers import get_relevant_financial_years
    relevant_fys = get_relevant_financial_years()
    current_fy = relevant_fys[2]  # Current year is at index 2
    
    # Ensure Current FY Folder Exists
    try:
        file_meta = drive_svc.files().get(fileId=file_id, fields='parents', supportsAllDrives=True).execute()
        parents = file_meta.get('parents', [])
        if parents:
            viable_repo_id = parents[0]
            repo_meta = drive_svc.files().get(fileId=viable_repo_id, fields='parents', supportsAllDrives=True).execute()
            repo_parents = repo_meta.get('parents', [])
            if repo_parents:
                entity_root_id = repo_parents[0]
                create_folder_structure(drive_svc, current_fy, entity_root_id, entity_type, company_name)
    except Exception as e:
        logger.error(f"Failed to auto-create Current FY folder structure: {e}")
    
    # Dynamic Path Map Generation
    try:
        json_path = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'entity_folder_structures.json')
        with open(json_path, 'r') as f:
            folder_structures = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load entity_folder_structures.json: {e}")
        folder_structures = {}
    
    entity_structure = folder_structures.get(entity_type, folder_structures.get("india", {}))
    
    # Identify the Financial Docs key
    fin_key = None
    for k in entity_structure.keys():
        if "Financial Related Docs" in k:
            fin_key = k
            break
    
    full_structure_for_mapping = entity_structure.copy()
    
    if fin_key:
        financial_docs_structure_dynamic = get_financial_docs_structure(entity_type, company_name)
        existing_children = full_structure_for_mapping[fin_key].copy()
        existing_children[f"FY {current_fy}"] = financial_docs_structure_dynamic
        full_structure_for_mapping[fin_key] = existing_children
    
    if not fin_key:
        fin_docs_root_name = "2. Financial Related Docs (Accounting, Audit & Taxation)" if entity_type == "india" else "2. Financial Related Docs"
        full_structure_for_mapping[fin_docs_root_name] = {
            f"FY {current_fy}": get_financial_docs_structure(entity_type, company_name)
        }
    
    # Define keys to exclude from Dropdown
    EXCLUDED_KEYS = {
        "0. Docs Repo", "Inflow", "Outflow",
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
        "1.Jan", "2.Feb", "3.Mar", "4.Apr", "5.May", "6.Jun",
        "7.Jul", "8.Aug", "9.Sep", "10.Oct", "11.Nov", "12.Dec",
        "1.Apr", "2.May", "3.Jun", "4.Jul", "5.Aug", "6.Sep",
        "7.Oct", "8.Nov", "9.Dec", "10.Jan", "11.Feb", "12.Mar"
    }
    
    def flatten_paths(structure, prefix=""):
        flat_map = {}
        for key, value in structure.items():
            current_full_path = f"{prefix}>>>{key}" if prefix else key
            readable_key = key
            if readable_key not in EXCLUDED_KEYS:
                flat_map[readable_key] = current_full_path
            if isinstance(value, dict) and value:
                flat_map.update(flatten_paths(value, current_full_path))
        return flat_map
    
    path_map_dict = flatten_paths(full_structure_for_mapping)
    path_map_json = json.dumps(path_map_dict)
    
    # Define Apps Script Code (complete implementation matching main app)
    code = f"""
    // Generated PathMap
    var pathMap = {path_map_json};

    function onOpen() {{
      var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
      sheet.getRange("AE2:AE").setDataValidation(
        SpreadsheetApp.newDataValidation()
          .requireValueInList(["Inflow", "Outflow", "Others"], true)
          .setAllowInvalid(false)
          .build()
      );

      sheet.getRange("AH2:AH").setDataValidation(
        SpreadsheetApp.newDataValidation()
          .requireValueInList(["Yes", "No", "Processed"], true)
          .setAllowInvalid(false)
          .build()
      );
    
      var destinationPaths = Object.keys(pathMap);
      sheet.getRange("AF2:AF").setDataValidation(
        SpreadsheetApp.newDataValidation()
          .requireValueInList(destinationPaths, true)
          .setAllowInvalid(false)
          .build()
      );
    
      createTrigger();
    }}
    
    function onEdit(e) {{
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var sheet = e.range.getSheet();
      var row = e.range.getRow();
      var col = e.range.getColumn();
    
      // ✅ START: Cascading Logic Across All Sheets
      if (row > 1) {{
        var editedHeaders = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
        var editedHeader = editedHeaders[col - 1];
        if (!editedHeader || editedHeader.toLowerCase() === "client id") return;
    
        var clientIdCol = editedHeaders.findIndex(h => h.toLowerCase() === "client id");
        if (clientIdCol === -1) return;
    
        var clientId = sheet.getRange(row, clientIdCol + 1).getValue();
        if (!clientId) return;
    
        var editedValue = e.value;
    
        var allSheets = ss.getSheets();
        allSheets.forEach(function (targetSheet) {{
          // Skip same sheet and same row
          if (targetSheet.getName() === sheet.getName()) return;
    
          var targetHeaders = targetSheet.getRange(1, 1, 1, targetSheet.getLastColumn()).getValues()[0];
          var targetClientIdCol = targetHeaders.findIndex(h => h.toLowerCase() === "client id");
          var targetColToUpdate = targetHeaders.findIndex(h => h.toLowerCase().trim() === editedHeader.toLowerCase().trim());
    
          if (targetClientIdCol === -1 || targetColToUpdate === -1) return;
    
          var lastRow = targetSheet.getLastRow();
          if (lastRow < 2) return;
    
          var targetClientIds = targetSheet.getRange(2, targetClientIdCol + 1, lastRow - 1).getValues();
    
          for (var i = 0; i < targetClientIds.length; i++) {{
            if (String(targetClientIds[i][0]) === String(clientId)) {{
              targetSheet.getRange(i + 2, targetColToUpdate + 1).setValue(editedValue);
              break; // Assuming one row per Client ID per sheet
            }}
          }}
        }});
      }}
      // ✅ END: Cascading Logic
    
      var fileLinkCol = 8; // H (1-based index)
      var moveCol = 32;    // AF (1-based index)
      if (col === moveCol && row > 1) {{
        var fileLink = sheet.getRange(row, fileLinkCol).getValue();
        var selectedShortPath = e.value;
        var selectedPath = pathMap[selectedShortPath]; // Lookup full path
        var baseFolderName = SpreadsheetApp.getActiveSpreadsheet().getName().replace(/ workbook$/i, "");
    
        if (fileLink && selectedPath) {{
          try {{
            var fileId = getFileIdFromUrl(fileLink);
            if (!fileId) throw new Error("Invalid file link");
            var note = moveFileToPath(fileId, selectedPath, baseFolderName);
            sheet.getRange(row, moveCol).setNote(note);
          }} catch (err) {{
            sheet.getRange(row, moveCol).setNote("❌ " + err.message);
          }}
        }} else {{
          if (!selectedPath) {{
             sheet.getRange(row, moveCol).setNote("❌ Full path not found for selection.");
          }} else {{
             sheet.getRange(row, moveCol).setNote("❌ File link or selected path is empty.");
          }}
        }}
      }}
    
      if (row >= 2) {{
        highlightDuplicateInvoices(sheet, 15, 10); // Column O=15, Column J=10
      }}
    }}
    
    function findBaseFolderForFile(file, baseFolderName) {{
      var parents = file.getParents();
      if (!parents.hasNext()) return null;
    
      var folder = parents.next();
      while (folder) {{
        if (folder.getName() === baseFolderName) {{
          return folder;
        }}
        var gpIter = folder.getParents();
        if (!gpIter.hasNext()) {{
          return null;
        }}
        folder = gpIter.next();
      }}
      return null;
    }}
    
    function getSubFolderFromBase(baseFolder, path) {{
      var folder = baseFolder;
      var parts = path.split(">>>");
    
      for (var i = 0; i < parts.length; i++) {{
        var name = parts[i];
        var it = folder.getFoldersByName(name);
        if (!it.hasNext()) {{
          return null;
        }}
        folder = it.next();
      }}
      return folder;
    }}
    
    
    function moveFileToPath(fileId, destinationPath, baseFolderName) {{
      try {{
        // Get the file (works with shared drives now that Drive scope is granted)
        var file = DriveApp.getFileById(fileId);
    
        // 1. Find the correct entity root for THIS file by walking up
        var baseFolder = findBaseFolderForFile(file, baseFolderName);
        if (!baseFolder) {{
          throw new Error("Base folder '" + baseFolderName + "' not found in file ancestry.");
        }}
    
        // 2. From that base, walk down the >>> path (e.g. 0. Viable Repo>>>0. Docs Repo>>>Valid)
        var destFolder = getSubFolderFromBase(baseFolder, destinationPath);
        if (!destFolder) {{
          throw new Error("Destination folder not found: " + destinationPath);
        }}
    
        var destFolderId = destFolder.getId();
    
        // 3. Read current parents via Drive Advanced Service (v2, supportsAllDrives)
        var meta = Drive.Files.get(fileId, {{ supportsAllDrives: true }});
        var parents = meta.parents || [];
        var previousParents = parents.map(function (p) {{ return p.id; }}).join(",");
    
        // 4. Move using addParents/removeParents
        if (!previousParents) {{
          // No recorded parents – just add the new one
          Drive.Files.update(
            {{}},
            fileId,
            null,
            {{
              addParents: destFolderId,
              supportsAllDrives: true
            }}
          );
        }} else {{
          Drive.Files.update(
            {{}},
            fileId,
            null,
            {{
              addParents: destFolderId,
              removeParents: previousParents,
              supportsAllDrives: true
            }}
          );
        }}
    
        return "✅ Moved to: " + baseFolder.getName() + ">>>" + destinationPath;
      }} catch (err) {{
        var msg = String(err);
        Logger.log("moveFileToPath error for " + fileId + ": " + msg);
    
        if (msg.indexOf("must have exactly one parent") !== -1) {{
          return (
            "❌ Drive reports this file has an invalid parent state (shared-drive multi-parent). " +
            "Open the file from this link, check 'Show file location', " +
            "normalise it to a single location in the correct entity tree, then retry."
          );
        }}
    
        return "❌ " + err.message + " (Target: " + destinationPath + ", Base: " + baseFolder.getName() + ")";
      }}
    }}
    
    function moveRowToSheet(sourceSheetName, destSheetName, rowNumber) {{
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var sourceSheet = ss.getSheetByName(sourceSheetName);
      var destSheet = ss.getSheetByName(destSheetName);
      if (!sourceSheet || !destSheet) return;
      var rowData = sourceSheet.getRange(rowNumber, 1, 1, sourceSheet.getLastColumn()).getValues()[0];
      destSheet.appendRow(rowData);
    }}
    
    function removeRowFromSheets(sheetNames, rowData, idColIndex) {{
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      for (var i = 0; i < sheetNames.length; i++) {{
        var sheet = ss.getSheetByName(sheetNames[i]);
        if (!sheet) continue;
        var data = sheet.getDataRange().getValues();
        for (var r = 1; r < data.length; r++) {{
          if (data[r][idColIndex] === rowData[idColIndex]) {{
            sheet.deleteRow(r + 1);
            break;
          }}
        }}
      }}
    }}
    
    function getFileIdFromUrl(url) {{
      var match = url.match(/[-\\w]{{25,}}/);
      return match ? match[0] : null;
    }}
    
    function getSubFolderByPath(baseFolderName, path) {{
      var baseFolders = DriveApp.getFoldersByName(baseFolderName);
      if (!baseFolders.hasNext()) return null;
      var folder = baseFolders.next();
      var parts = path.split(">>>");
      for (var i = 0; i < parts.length; i++) {{
        var part = parts[i];
        var subFolders = folder.getFoldersByName(part);
        var found = false;
        while (subFolders.hasNext()) {{
          folder = subFolders.next();
          found = true;
          break;
        }}
        if (!found) return null;
      }}
      return folder;
    }}
    
    function highlightDuplicateInvoices(sheet, invoiceCol, duplicateCol) {{
      var lastRow = sheet.getLastRow();
      if (lastRow < 2) return;
      var invoiceValues = sheet.getRange(2, invoiceCol, lastRow - 1, 1).getValues();
      var duplicateValues = sheet.getRange(2, duplicateCol, lastRow - 1, 1).getValues();
      var clientIds = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
      var invoiceMap = {{}};
      for (var i = 0; i < invoiceValues.length; i++) {{
        var invoice = normalize(invoiceValues[i][0]);
        if (!invoice) {{
          duplicateValues[i][0] = "";
          continue;
        }}
        if (!(invoice in invoiceMap)) {{
          invoiceMap[invoice] = i;
          duplicateValues[i][0] = "";
        }} else {{
          duplicateValues[i][0] = clientIds[invoiceMap[invoice]][0];
        }}
      }}
      sheet.getRange(2, duplicateCol, lastRow - 1, 1).setValues(duplicateValues);
    }}
    
    function normalize(value) {{
      if (!value) return "";
      return String(value).trim().toLowerCase();
    }}
    
    function createTrigger() {{
      var triggers = ScriptApp.getProjectTriggers();
      var exists = triggers.some(function(t) {{
        return t.getHandlerFunction() === "onEdit";
      }});
      if (!exists) {{
        ScriptApp.newTrigger("onEdit")
          .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
          .onEdit()
          .create();
      }}
    }}
    """
    
    # Upload script content
    content = {
        "files": [
            {"name": "Code", "type": "SERVER_JS", "source": code},
            {"name": "appsscript", "type": "JSON", "source": json.dumps({
                "timeZone": "America/New_York",
                "dependencies": {},
                "exceptionLogging": "STACKDRIVER",
                "runtimeVersion": "V8",
                "oauthScopes": [
                    "https://www.googleapis.com/auth/drive.readonly",
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/script.external_request",
                    "https://www.googleapis.com/auth/drive",
                    "https://www.googleapis.com/auth/script.scriptapp"
                ]
            })}
        ]
    }
    
    script_service.projects().updateContent(scriptId=script_id, body=content).execute()
    logger.info(f"Attached validation script to spreadsheet {file_id}")
