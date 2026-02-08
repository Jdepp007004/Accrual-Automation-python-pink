"""
Shared utilities for N8N workflows and Flask frontend.
These modules can be imported in N8N code nodes.
"""

from .email_helpers import normalize_name, get_company_info, build_processed_label_name
from .file_helpers import build_updated_filename, create_folder_hierarchy, compute_hash
from .google_auth import get_google_services
from .gemini_client import analyze_document_with_gemini

__all__ = [
    'normalize_name',
    'get_company_info', 
    'build_processed_label_name',
    'build_updated_filename',
    'create_folder_hierarchy',
    'compute_hash',
    'get_google_services',
    'analyze_document_with_gemini',
]
