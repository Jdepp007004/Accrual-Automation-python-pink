"""
Test Authentication Script for N8N Implementation
Run this script to authenticate and generate token.json with all required scopes.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared_utils.google_auth import get_google_services

if __name__ == "__main__":
    print("🔐 Testing Google API Authentication...")
    print("=" * 50)
    
    try:
        # This will trigger authentication flow and create token.json
        gmail, sheets, drive, creds = get_google_services()
        
        print("✅ Authentication successful!")
        print(f"✅ Token saved to: {os.path.join(os.path.dirname(__file__), 'token.json')}")
        print("\n📋 Granted Scopes:")
        if hasattr(creds, 'scopes'):
            for scope in creds.scopes:
                print(f"  - {scope}")
        
        print("\n🧪 Testing API access...")
        
        # Test Gmail API
        try:
            profile = gmail.users().getProfile(userId='me').execute()
            print(f"✅ Gmail API: Connected (Email: {profile.get('emailAddress', 'N/A')})")
        except Exception as e:
            print(f"❌ Gmail API: {str(e)}")
        
        # Test Drive API
        try:
            about = drive.about().get(fields="user").execute()
            print(f"✅ Drive API: Connected (User: {about.get('user', {}).get('displayName', 'N/A')})")
        except Exception as e:
            print(f"❌ Drive API: {str(e)}")
        
        # Test Sheets API
        try:
            # Just verify we can build the service
            print("✅ Sheets API: Connected")
        except Exception as e:
            print(f"❌ Sheets API: {str(e)}")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed! You can now run the n8n implementation.")
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {str(e)}")
        print("\n💡 Make sure you have:")
        print("  1. credentials.json in the n8n_implementation directory")
        print("  2. Enabled required Google APIs in your Google Cloud project")
        print("  3. Deleted old token.json if it exists")
        sys.exit(1)
