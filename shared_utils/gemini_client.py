"""
Google Gemini AI client for document analysis in N8N workflows.
"""

import time
import google.generativeai as genai
from typing import List, Dict, Any


def configure_gemini(api_key: str):
    """
    Configure Gemini API with the provided API key.
    
    Args:
        api_key: Google Gemini API key
    """
    genai.configure(api_key=api_key)


def analyze_document_with_gemini(
    file_data: bytes,
    mime_type: str,
    api_key: str = None,
    max_retries: int = 3
) -> List[Dict[str, Any]]:
    """
    Analyze a document using Google Gemini AI to extract invoice details.
    
    Args:
        file_data: File content as bytes
        mime_type: MIME type of the file
        api_key: Optional Gemini API key (if not already configured)
        max_retries: Maximum number of retry attempts
        
    Returns:
        List of document dictionaries with extracted fields
    """
    if api_key:
        configure_gemini(api_key)
    
    prompt = """
    You are an expert OCR and document analysis assistant. Analyze the provided document image or PDF and extract the following information for EACH document/invoice found in the image. If multiple invoices or documents are present in a single image, return an array with separate entries for each.

    For each document, extract these fields and return as a JSON object:
    - Document Type: Invoice, Receipt, Credit Note, Debit Note, Purchase Order, etc.
    - Seller Name: Full legal name of the seller/supplier
    - Buyer Name: Full legal name of the buyer/customer
    - Doc Number: Invoice/Document number
    - Invoice Date: Date in "DD Mon YYYY" format (e.g., "15 Jan 2024")
    - Invoice Month: Month number (1-12)
    - Invoice Month Name: Full month name (e.g., "January")
    - Invoice Year: Year (YYYY)
    - Currency: Currency code with symbol in format "CODE(Symbol)" (e.g., "USD($)", "INR(₹)")
    - Total Amount: Total payable amount (numeric only, no currency symbols)
    - Gross Amount: Amount before taxes
    - GST: Total GST/Tax amount
    - TDS: TDS amount (if applicable)
    - Other Taxes: Any other taxes
    - Net Amount: Net payable amount
    - CGST: Central GST (for India)
    - SGST: State GST (for India)
    - IGST: Integrated GST (for India)
    - GST Percentage: GST rate as percentage (e.g., "18%") - can be array if multiple rates
    - Seller State: State of seller
    - Buyer State: State of buyer
    - Seller GSTIN: Seller's GSTIN/Tax ID
    - Buyer GSTIN: Buyer's GSTIN/Tax ID
    - Seller PAN: Seller's PAN (if available)
    - Buyer PAN: Buyer's PAN (if available)
    - HSN/SAC: HSN or SAC codes - can be array if multiple

    CRITICAL RULES:
    1. Return ONLY a valid JSON array, even if there's just one document: [{ ... }]
    2. If a field is not found, use empty string ""
    3. For numeric fields, return only the number without currency symbols or commas
    4. Dates must be in "DD Mon YYYY" format (e.g., "05 Feb 2024")
    5. Currency must be in "CODE(Symbol)" format
    6. Do not include any explanatory text, only the JSON array
    7. If multiple documents are in the image, create separate objects in the array
    8. Ensure all quotes and braces are properly escaped in JSON
    
    Example output format:
    [
        {
            "Document Type": "Invoice",
            "Seller Name": "ABC Corp Pvt Ltd",
            "Buyer Name": "XYZ Industries",
            "Doc Number": "INV-2024-001",
            "Invoice Date": "15 Jan 2024",
            "Invoice Month": "1",
            "Invoice Month Name": "January",
            "Invoice Year": "2024",
            "Currency": "INR(₹)",
            "Total Amount": "11800",
            "Gross Amount": "10000",
            "GST": "1800",
            "CGST": "900",
            "SGST": "900",
            "IGST": "",
            "GST Percentage": "18%",
            "Seller GSTIN": "29AABCT1332L1Z5",
            "Buyer GSTIN": "27AADCB2231M1ZP",
            "HSN/SAC": "998314"
        }
    ]
    
    Now analyze the provided document and return the JSON array:
    """
    
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    # Prepare the parts for the model
    parts = [
        {"mime_type": mime_type, "data": file_data},
        prompt
    ]
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(parts)
            
            # Extract JSON from response
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            text = text.strip()
            
            # Parse JSON
            import json
            documents = json.loads(text)
            
            # Ensure it's a list
            if not isinstance(documents, list):
                documents = [documents]
            
            return documents
            
        except Exception as e:
            if attempt < max_retries - 1:
                # Wait before retrying (exponential backoff)
                wait_time = (2 ** attempt) * 2
                time.sleep(wait_time)
                continue
            else:
                # Last attempt failed
                raise Exception(f"Gemini analysis failed after {max_retries} attempts: {str(e)}")
    
    return []
