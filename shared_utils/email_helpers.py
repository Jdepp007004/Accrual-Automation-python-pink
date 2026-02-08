"""
Email processing helper functions for N8N workflows.
These functions are standalone and can be imported in N8N code nodes.
"""

import unicodedata
import re


def normalize_name(name: str) -> str:
    """Normalize a name for consistent comparison."""
    clean = unicodedata.normalize("NFKC", name)
    clean = re.sub(r"[\u200B-\u200F\u202A-\u202E\u2060]", "", clean)
    return clean.strip().lower()


def get_company_info(aliases_data: dict, label_name: str) -> dict:
    """
    Get company information from aliases data.
    
    Args:
        aliases_data: Dictionary of company aliases and info
        label_name: Name of the label/company to look up
        
    Returns:
        Dictionary with company name, entity_type, and aliases
    """
    label_norm = normalize_name(label_name)
    
    for company, info in aliases_data.items():
        if normalize_name(company) == label_norm:
            return {"name": company, **info}
    
    # Default fallback if not found
    return {"name": label_name, "entity_type": "india", "aliases": []}


def ensure_label_exists(gmail, label_name: str) -> str:
    """
    Ensure a Gmail label exists, creating it if necessary.
    Returns the label ID.
    
    Args:
        gmail: Gmail API service object
        label_name: Name of the label (can include hierarchy with /)
        
    Returns:
        Label ID string
    """
    all_labels = gmail.users().labels().list(userId="me").execute().get("labels", [])
    
    # Check if label already exists
    for lbl in all_labels:
        if lbl["name"] == label_name:
            return lbl["id"]
    
    # Create label hierarchy
    parts = label_name.split("/")
    parent_id = None
    
    for i in range(len(parts)):
        current_label = "/".join(parts[:i+1])
        
        # Check if this level exists
        existing = next((lbl for lbl in all_labels if lbl["name"] == current_label), None)
        
        if existing:
            parent_id = existing["id"]
        else:
            # Create new label
            label_body = {
                "name": current_label,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show"
            }
            
            created = gmail.users().labels().create(userId="me", body=label_body).execute()
            parent_id = created["id"]
            all_labels.append(created)
    
    return parent_id


def build_processed_label_name(gmail, root_label: str, entity_name: str = None) -> str:
    """
    Constructs the name for the 'processed' label, ensuring it exists in Gmail.
    Returns the label ID.
    
    Args:
        gmail: Gmail API service object
        root_label: Root label name
        entity_name: Optional entity name for multi-entity setup
        
    Returns:
        Processed label ID
    """
    all_labels = gmail.users().labels().list(userId="me").execute().get("labels", [])
    
    if entity_name:
        accruals_label_name = f"{root_label}/{entity_name}/Docs"
        accruals_exists = any(lbl["name"] == accruals_label_name for lbl in all_labels)
        
        if accruals_exists:
            processed_label_name = f"{accruals_label_name}/Processed"
        else:
            processed_label_name = f"{root_label}/{entity_name}/Processed"
    else:
        accruals_label_name = f"{root_label}/Docs"
        accruals_exists = any(lbl["name"] == accruals_label_name for lbl in all_labels)
        
        if accruals_exists:
            processed_label_name = f"{accruals_label_name}/Processed"
        else:
            processed_label_name = f"{root_label}/Processed"
    
    return ensure_label_exists(gmail, processed_label_name)
