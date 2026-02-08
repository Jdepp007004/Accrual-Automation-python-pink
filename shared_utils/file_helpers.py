"""
File processing helper functions for N8N workflows.
These functions are standalone and can be imported in N8N code nodes.
"""

import re
import hashlib
from datetime import datetime
from typing import Dict, Any


def safe_str(value) -> str:
    """Convert any value to a safe, stripped string."""
    if value is None:
        return ""
    return str(value).strip()


def compute_hash(file_bytes: bytes) -> str:
    """
    Compute SHA256 hash of file content for duplicate detection.
    
    Args:
        file_bytes: File content as bytes
        
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(file_bytes).hexdigest()


def build_updated_filename(doc: dict, entity_name: str) -> str:
    """
    Build standardized filename from document metadata.
    Format: DD.MM.YYYY_EntityName_CODE (Symbol) Amount
    
    Args:
        doc: Document metadata dictionary from Gemini analysis
        entity_name: Name of the entity for the filename
        
    Returns:
        Formatted filename string (without extension)
    """
    # Extract and normalize invoice date
    raw_date = safe_str(doc.get("Invoice Date")).strip()
    updated_date = ""
    
    if raw_date:
        try:
            # Parse date in "DD Mon YYYY" format
            date_obj = datetime.strptime(raw_date, "%d %b %Y")
            # Create new "Updated Invoice Date" key in "DD MM YYYY" format
            updated_date = date_obj.strftime("%d.%m.%Y")
            doc["Updated Invoice Date"] = updated_date
        except ValueError:
            # In case the format doesn't match
            updated_date = raw_date
            doc["Updated Invoice Date"] = ""
    else:
        doc["Updated Invoice Date"] = ""
    
    # For backward compatibility — replace dashes with dots
    date_str = updated_date.replace("-", ".") if updated_date else ""
    
    entity = safe_str(entity_name).title()
    currency_raw = safe_str(doc.get("Currency"))
    amount_str = safe_str(doc.get("Total Amount"))
    
    try:
        amount_val = float(amount_str.replace(",", ""))
        amount = f"{amount_val:,.2f}"
    except (ValueError, TypeError):
        amount = amount_str
    
    # Parse Currency and Symbol from OCR output (Expected: "USD($)" or "USD ($)")
    currency_code = currency_raw
    symbol = "?"
    
    # regex to match "CODE (Symbol)" or "CODE(Symbol)"
    match = re.search(r"([A-Za-z]+)\s*\((.+)\)", currency_raw)
    if match:
        currency_code = match.group(1).strip()
        symbol = match.group(2).strip()
    
    if currency_raw or amount:
        # Format: CODE (Symbol) Amount
        if currency_code:
            currency_amount = f"{currency_code} ({symbol}) {amount}"
        else:
            currency_amount = amount  # fallback if no currency at all
    else:
        currency_amount = ""
    
    # Build filename
    parts = [date_str, entity, currency_amount]
    filename = "_".join([p for p in parts if p]) or "Unknown_File"
    
    return filename


def create_folder_hierarchy(drive, parent_id: str, structure: dict) -> dict:
    """
    Recursively create folder hierarchy in Google Drive.
    
    Args:
        drive: Google Drive API service object
        parent_id: Parent folder ID where to create structure
        structure: Dictionary representing folder hierarchy
        
    Returns:
        Dictionary mapping folder names to their IDs
    """
    from .google_auth import find_or_create_folder
    
    folder_ids = {}
    
    for folder_name, subfolders in structure.items():
        folder_id = find_or_create_folder(drive, folder_name, parent_id)
        folder_ids[folder_name] = folder_id
        
        if isinstance(subfolders, dict) and subfolders:
            subfolder_ids = create_folder_hierarchy(drive, folder_id, subfolders)
            folder_ids.update(subfolder_ids)
    
    return folder_ids


def to_float(value) -> float:
    """
    Convert value to float, handling common formatting issues.
    
    Args:
        value: Value to convert (can be int, float, or string)
        
    Returns:
        Float value or 0.0 if conversion fails
    """
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        value = value.replace(",", "").strip()
        if value:
            try:
                return float(value)
            except ValueError:
                return 0.0
    return 0.0
