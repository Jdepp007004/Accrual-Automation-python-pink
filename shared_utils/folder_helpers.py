"""
Folder hierarchy management utilities.
"""

from datetime import datetime


def create_folder_hierarchy(drive, parent_id: str, structure: dict):
    """
    Recursively create folder hierarchy from structure definition.
    
    Args:
        drive: Google Drive API service object
        parent_id: Parent folder ID
        structure: Dictionary defining folder structure
        
    Returns:
        Dict of created folder IDs
    """
    from .google_auth import find_or_create_folder
    
    folder_ids = {}
    
    for folder_name, subfolders in structure.items():
        # Create this folder
        folder_id = find_or_create_folder(drive, folder_name, parent_id)
        folder_ids[folder_name] = folder_id
        
        # Recursively create subfolders
        if isinstance(subfolders, dict) and subfolders:
            child_ids = create_folder_hierarchy(drive, folder_id, subfolders)
            folder_ids.update(child_ids)
    
    return folder_ids


def get_relevant_financial_years():
    """
    Calculates the last 2, current, and next 1 financial years based on today's date.
    Financial Year is assumed to be April 1st to March 31st.
    Returns a list of strings like "2024-2025".
    """
    today = datetime.now()
    
    # Determine current FY start year
    # If before April, we are in the FY starting previous year.
    # E.g., Jan 2026 -> FY 2025-2026 (Start 2025)
    # E.g., May 2026 -> FY 2026-2027 (Start 2026)
    curr_fy_start = today.year if today.month >= 4 else today.year - 1
    
    years = []
    # Last 2, Current, Next 1 -> Range from -2 to +1 relative to current
    for i in range(-2, 2): 
        start = curr_fy_start + i
        end = start + 1
        years.append(f"{start}-{end}")
        
    return years
