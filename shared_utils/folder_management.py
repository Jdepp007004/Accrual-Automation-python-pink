"""
Folder structure management utilities.
"""


def create_folder_hierarchy(drive, parent_id: str, structure: dict):
    """
    Recursively create folder hierarchy from structure definition.
    
    Args:
        drive: Google Drive API service object
        parent_id: Parent folder ID
        structure: Dictionary defining folder structure
    """
    from shared_utils.google_auth import find_or_create_folder
    
    for folder_name, subfolders in structure.items():
        # Create this folder
        folder_id = find_or_create_folder(drive, folder_name, parent_id)
        
        # Recursively create subfolders
        if isinstance(subfolders, dict) and subfolders:
            create_folder_hierarchy(drive, folder_id, subfolders)


def validate_and_create_folder_structure(drive, entity_name: str, entity_folder_id: str, entity_type: str):
    """
    Validate and create complete folder structure for an entity.
    
    Args:
        drive: Google Drive API service object
        entity_name: Name of the entity
        entity_folder_id: Root folder ID for the entity
        entity_type: Type of entity ('india' or 'us')
        
    Returns:
        dict: Summary of created folders
    """
    import json
    import os
    
    # Load folder structure definition
    structure_path = os.path.join(os.path.dirname(__file__), '..', 'entity_folder_structures.json')
    with open(structure_path, 'r') as f:
        all_structures = json.load(f)
    
    # Get structure for this entity type
    structure = all_structures.get(entity_type, all_structures.get('india'))
    
    # Create all folders recursively
    create_folder_hierarchy(drive, entity_folder_id, structure)
    
    return {
        "entity": entity_name,
        "entity_type": entity_type,
        "status": "completed",
        "message": f"Folder structure validated and created for {entity_name}"
    }
