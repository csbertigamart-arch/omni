import os
import json
import pickle
from typing import Dict, List, Optional
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import gspread
import logging
from file_system_manager import FileSystemManager


class GoogleSheetsManager:
    """Manage Google Sheets OAuth authentication and sheet operations"""

    # Gunakan scope yang lebih spesifik
    SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly'
    ]

    def __init__(self, fs_manager: FileSystemManager):
        self.fs = fs_manager
        self.credentials_file = self.fs.get_full_path(
            "config", "google_credentials.json")
        self.token_file = self.fs.get_full_path(
            "config", "google_token.pickle")
        self.settings_file = self.fs.get_full_path(
            "config", "google_sheets_settings.json")
        self.creds = None
        self.service = None
        self._load_settings()
        self._authenticate()
        self.logger = logging.getLogger(__name__)  # TAMBAH INI

    def _load_settings(self):
        """Load Google Sheets settings"""
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                "spreadsheet_id": "",
                "selected_sheet": "",
                "manual_mode": False,
                "available_spreadsheets": [],
                "available_worksheets": []
            }
            self._save_settings()

    def _save_settings(self):
        """Save Google Sheets settings"""
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2)

    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            # Check if token file exists and is valid
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)

            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                        print("✅ Token refreshed successfully")
                    except Exception as refresh_error:
                        print(f"❌ Token refresh failed: {refresh_error}")
                        self.creds = None
                else:
                    self.creds = None
                    return False

                # Save refreshed token
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.creds, token)

            if self.creds and self.creds.valid:
                self.service = build('sheets', 'v4', credentials=self.creds)
                print("✅ Google Sheets service initialized")
                return True
            else:
                print("❌ Invalid credentials")
                return False

        except Exception as e:
            print(f"❌ Google authentication error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def get_auth_url(self) -> str:
        """Get Google OAuth authentication URL - FIXED VERSION"""
        try:
            if not os.path.exists(self.credentials_file):
                print("❌ Credentials file not found")
                return ""

            # Use the same redirect URI as configured in Google Cloud Console
            redirect_uri = 'http://localhost:5000/api/google/auth/callback'

            print(f"🔗 Using redirect URI: {redirect_uri}")
            print(f"📋 Requested scopes: {self.SCOPES}")

            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.SCOPES,  # Scopes are set here during initialization
                redirect_uri=redirect_uri
            )

            # Generate authorization URL WITHOUT explicit scope parameter
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='false',
                prompt='consent'
                # Remove the scope parameter from here since it's already set above
            )

            print(f"✅ Generated auth URL successfully")
            print(f"   State parameter: {state}")
            return auth_url

        except Exception as e:
            print(f"❌ Error generating auth URL: {str(e)}")
            import traceback
            traceback.print_exc()
            return ""

    def handle_callback(self, code: str) -> bool:
        """Handle OAuth callback and exchange code for tokens - PERBAIKAN SCOPE HANDLING"""
        try:
            print(f"🔄 Handling OAuth callback with code: {code[:20]}...")

            if not code or code == "None":
                print("❌ No authorization code provided in callback")
                return False

            if not os.path.exists(self.credentials_file):
                print("❌ Credentials file not found")
                return False

            # Use the same redirect URI as in auth URL
            redirect_uri = 'http://localhost:5000/api/google/auth/callback'

            print(f"🔗 Using redirect URI: {redirect_uri}")

            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                self.SCOPES,
                redirect_uri=redirect_uri,
                state=None
            )

            # Exchange authorization code for tokens with scope validation disabled
            print("🔄 Exchanging code for tokens...")
            try:
                # Disable scope verification untuk menghindari masalah scope change
                flow.oauth2session._client._scope_changed = lambda *args, **kwargs: False

                flow.fetch_token(code=code)
                self.creds = flow.credentials

                # DEBUG: Print all token information
                print(f"✅ Token exchange successful!")
                print(f"   Access Token: {self.creds.token[:20]}...")
                print(
                    f"   Refresh Token: {'Yes' if self.creds.refresh_token else 'No'}")
                print(f"   Token Expiry: {self.creds.expiry}")
                print(f"   Scopes: {self.creds.scopes}")
                print(f"   Valid: {self.creds.valid}")
                print(f"   Expired: {self.creds.expired}")

                # Check if we have the basic token properties
                if not self.creds.token:
                    print("❌ No access token received")
                    return False

                print("✅ Token validation passed")

            except Exception as token_error:
                print(f"❌ Token exchange failed: {str(token_error)}")
                # Coba lagi tanpa validasi scope
                try:
                    print("🔄 Retrying token exchange without scope validation...")
                    flow = Flow.from_client_secrets_file(
                        self.credentials_file,
                        scopes=None,  # Tidak set scope untuk menghindari validasi
                        redirect_uri=redirect_uri,
                        state=None
                    )
                    flow.fetch_token(code=code)
                    self.creds = flow.credentials
                    print("✅ Token exchange successful on retry!")
                except Exception as retry_error:
                    print(f"❌ Retry also failed: {str(retry_error)}")
                    return False

            # Save credentials
            try:
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.creds, token)
                print(f"✅ Credentials saved to {self.token_file}")
            except Exception as save_error:
                print(f"❌ Failed to save credentials: {str(save_error)}")
                return False

            # Rebuild service and test it
            try:
                self.service = build('sheets', 'v4', credentials=self.creds)
                print("✅ Google Sheets service reinitialized")

                # Test the service with a simple API call
                print("🔧 Testing Google Sheets API connection...")
                try:
                    # Try to get user profile to verify authentication
                    drive_service = build(
                        'drive', 'v3', credentials=self.creds)
                    about = drive_service.about().get(fields="user").execute()
                    user_email = about.get('user', {}).get(
                        'emailAddress', 'Unknown')
                    print(f"✅ API test successful! Connected as: {user_email}")
                except Exception as api_test_error:
                    print(f"⚠️ API test warning: {str(api_test_error)}")
                    print("ℹ️ Authentication successful but API test had issues")

                return True

            except Exception as service_error:
                print(f"❌ Failed to build service: {str(service_error)}")
                return False

        except Exception as e:
            print(f"❌ Error handling callback: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _load_available_spreadsheets(self):
        """Load available spreadsheets after authentication - FIXED VERSION"""
        try:
            if not self.is_authenticated():
                print("❌ Not authenticated for loading spreadsheets")
                return

            print("🔄 Loading spreadsheets from Google Drive...")
            drive_service = build('drive', 'v3', credentials=self.creds)
            results = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                pageSize=100,
                fields="files(id, name, createdTime, modifiedTime)"
            ).execute()

            spreadsheets = results.get('files', [])
            print(f"📊 Found {len(spreadsheets)} spreadsheets from Google Drive")

            # Update settings
            self.settings["available_spreadsheets"] = [
                {
                    'id': sheet['id'],
                    'name': sheet['name'],
                    'created_time': sheet.get('createdTime', ''),
                    'modified_time': sheet.get('modifiedTime', '')
                }
                for sheet in spreadsheets
            ]

            self._save_settings()
            print(f"✅ Loaded {len(spreadsheets)} spreadsheets into settings")

        except Exception as e:
            print(f"❌ Error loading spreadsheets: {str(e)}")
            import traceback
            traceback.print_exc()
            # Don't clear existing data on error
    def get_spreadsheets(self) -> List[Dict]:
        """Get list of available spreadsheets"""
        if not self.is_authenticated():
            print("❌ Not authenticated for getting spreadsheets")
            return []

        # Gunakan data yang sudah di-load, atau load ulang
        if not self.settings.get("available_spreadsheets"):
            self._load_available_spreadsheets()

        return self.settings.get("available_spreadsheets", [])

    def get_worksheets(self, spreadsheet_id: str) -> List[Dict]:
        """Get list of worksheets in a spreadsheet"""
        if not self.is_authenticated():
            print("❌ Not authenticated for getting worksheets")
            return []

        try:
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            sheets = sheet_metadata.get('sheets', [])
            worksheets = []

            for sheet in sheets:
                props = sheet['properties']
                worksheet_info = {
                    'title': props['title'],
                    'sheet_id': props['sheetId'],
                    'index': props.get('index', 0),
                    'sheet_type': props.get('sheetType', 'GRID')
                }
                worksheets.append(worksheet_info)

            print(f"📑 Found {len(worksheets)} worksheets in spreadsheet")

            # Simpan worksheets untuk spreadsheet ini
            self.settings["available_worksheets"] = worksheets
            self._save_settings()

            return worksheets

        except HttpError as error:
            print(f"❌ Error getting worksheets: {error}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error getting worksheets: {str(e)}")
            return []

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with Google"""
        return self.creds is not None and self.creds.valid

    def has_credentials_file(self) -> bool:
        """Check if credentials file exists"""
        return os.path.exists(self.credentials_file)

    def get_auth_status(self):
        """Get complete authentication status"""
        return {
            "authenticated": self.is_authenticated(),
            "settings": self.get_current_settings(),
            "has_credentials": self.has_credentials_file(),
            "available_spreadsheets": self.settings.get("available_spreadsheets", [])
        }

    def get_current_settings(self) -> Dict:
        """Get current Google Sheets settings"""
        return self.settings.copy()

    def test_connection(self, spreadsheet_id: str = None) -> bool:
        """Test connection to Google Sheets"""
        try:
            test_id = spreadsheet_id or self.settings.get("spreadsheet_id")
            if not test_id:
                print("❌ No spreadsheet ID provided for connection test")
                return False

            if self.settings.get("manual_mode"):
                print("ℹ️ Manual mode - skipping connection test")
                return True

            if not self.is_authenticated():
                print("❌ Not authenticated for connection test")
                return False

            # Try to get spreadsheet info
            self.service.spreadsheets().get(
                spreadsheetId=test_id
            ).execute()

            print("✅ Connection test successful")
            return True

        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            return False

    def logout(self):
        """Logout and clear credentials"""
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                print("✅ Token file removed")

            # Reset settings
            self.settings.update({
                "spreadsheet_id": "",
                "selected_sheet": "",
                "manual_mode": False,
                "available_spreadsheets": [],
                "available_worksheets": []
            })
            self._save_settings()

            self.creds = None
            self.service = None
            print("✅ Logged out successfully")
            return True
        except Exception as e:
            print(f"❌ Error during logout: {str(e)}")
            return False

    def create_spreadsheet(self, title):
        """Create new spreadsheet"""
        try:
            if not self.is_authenticated():
                return None

            # Create new spreadsheet
            spreadsheet_body = {
                'properties': {
                    'title': title
                }
            }

            spreadsheet = self.service.spreadsheets().create(body=spreadsheet_body).execute()

            # Add to available spreadsheets
            new_spreadsheet = {
                'id': spreadsheet['spreadsheetId'],
                'name': spreadsheet['properties']['title'],
                'created_time': spreadsheet['properties'].get('createdTime', ''),
                'modified_time': spreadsheet['properties'].get('modifiedTime', '')
            }

            # Update local list
            if 'available_spreadsheets' in self.settings:
                self.settings['available_spreadsheets'].append(new_spreadsheet)
            else:
                self.settings['available_spreadsheets'] = [new_spreadsheet]

            self._save_settings()

            print(
                f"✅ Created new spreadsheet: {title} ({spreadsheet['spreadsheetId']})")
            return new_spreadsheet

        except Exception as e:
            print(f"❌ Error creating spreadsheet: {str(e)}")
            return None

    def update_detailed_settings(self, wallet_spreadsheet_id, shipping_spreadsheet_id):
        """Update detailed spreadsheet settings"""
        try:
            self.settings.update({
                "wallet_spreadsheet_id": wallet_spreadsheet_id,
                "shipping_spreadsheet_id": shipping_spreadsheet_id,
                "manual_mode": False
            })

            self._save_settings()
            print(
                f"✅ Settings updated - Wallet: {wallet_spreadsheet_id}, Shipping: {shipping_spreadsheet_id}")
            return True
        except Exception as e:
            print(f"❌ Error updating detailed settings: {str(e)}")
            return False

    def upload_to_sheet(self, spreadsheet_id, sheet_name, data):
        """Upload data to specified spreadsheet and worksheet - FIXED VERSION"""
        try:
            if not self.is_authenticated():
                print("❌ Not authenticated with Google Sheets")
                return False

            # Validasi dan bersihkan nama sheet
            def clean_sheet_name(name):
                # Hapus karakter tidak valid
                invalid_chars = [':', '/', '?', '*', '[', ']']
                for char in invalid_chars:
                    name = name.replace(char, '')
                # Trim spasi dan batasi panjang
                name = name.strip()
                return name[:31]  # Maksimal 31 karakter

            clean_sheet_name = clean_sheet_name(sheet_name)
            print(
                f"🔄 Original sheet name: '{sheet_name}' -> Cleaned: '{clean_sheet_name}'")

            # Get the spreadsheet
            try:
                spreadsheet = self.service.spreadsheets().get(
                    spreadsheetId=spreadsheet_id
                ).execute()
            except HttpError:
                print(f"❌ Spreadsheet {spreadsheet_id} not found or no access")
                return False

            # Cek apakah worksheet sudah ada, jika tidak buat baru
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            sheets = sheet_metadata.get('sheets', [])
            sheet_exists = False
            sheet_id = None

            for sheet in sheets:
                props = sheet.get('properties', {})
                if props.get('title') == clean_sheet_name:
                    sheet_exists = True
                    sheet_id = props.get('sheetId')
                    break

            if not sheet_exists:
                print(f"📄 Creating new worksheet: '{clean_sheet_name}'")
                try:
                    # Buat worksheet baru
                    add_sheet_request = {
                        'addSheet': {
                            'properties': {
                                'title': clean_sheet_name
                            }
                        }
                    }

                    batch_update_request = {
                        'requests': [add_sheet_request]
                    }

                    result = self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body=batch_update_request
                    ).execute()

                    # Dapatkan sheet ID dari response
                    new_sheet_props = result.get('replies', [{}])[0].get(
                        'addSheet', {}).get('properties', {})
                    sheet_id = new_sheet_props.get('sheetId')
                    print(f"✅ Created new worksheet with ID: {sheet_id}")

                except Exception as create_error:
                    print(f"❌ Failed to create worksheet: {create_error}")
                    return False

            # Prepare the data for batch update
            try:
                # Clear existing data jika worksheet sudah ada
                if sheet_exists:
                    try:
                        clear_request = {
                            'range': f"'{clean_sheet_name}'!A:Z"
                        }
                        self.service.spreadsheets().values().clear(
                            spreadsheetId=spreadsheet_id,
                            range=clear_request['range'],
                            body={}
                        ).execute()
                        print(
                            f"🧹 Cleared existing data from {clean_sheet_name}")
                    except Exception as clear_error:
                        print(f"⚠️ Could not clear sheet: {clear_error}")

                # Update with new data
                batch_update_request = {
                    'valueInputOption': 'RAW',
                    'data': [{
                        'range': f"'{clean_sheet_name}'!A1",
                        'values': data,
                        'majorDimension': 'ROWS'
                    }]
                }

                result = self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=batch_update_request
                ).execute()

                print(
                    f"✅ Successfully uploaded {len(data)} rows to {clean_sheet_name}")
                return True

            except Exception as e:
                print(f"❌ Error updating sheet: {str(e)}")
                return False

        except Exception as e:
            print(f"❌ Error uploading to Google Sheets: {str(e)}")
            return False


    def refresh_spreadsheets(self) -> List[Dict]:
        """Refresh and reload the list of available spreadsheets - FIXED VERSION"""
        try:
            if not self.is_authenticated():
                print("❌ Not authenticated for refreshing spreadsheets")
                return []

            print("🔄 Refreshing spreadsheet list from Google Drive...")
            
            # Jangan clear data dulu, load dulu kemudian update
            try:
                # Reload from Google Drive
                drive_service = build('drive', 'v3', credentials=self.creds)
                results = drive_service.files().list(
                    q="mimeType='application/vnd.google-apps.spreadsheet'",
                    pageSize=100,
                    fields="files(id, name, createdTime, modifiedTime)"
                ).execute()

                spreadsheets = results.get('files', [])
                print(f"📊 Found {len(spreadsheets)} spreadsheets from Google Drive")

                # Update settings dengan data baru
                self.settings["available_spreadsheets"] = [
                    {
                        'id': sheet['id'],
                        'name': sheet['name'],
                        'created_time': sheet.get('createdTime', ''),
                        'modified_time': sheet.get('modifiedTime', '')
                    }
                    for sheet in spreadsheets
                ]

                self._save_settings()
                
                refreshed_count = len(spreadsheets)
                print(f"✅ Successfully refreshed {refreshed_count} spreadsheets")
                
                return self.settings["available_spreadsheets"]
                
            except Exception as load_error:
                print(f"❌ Error loading spreadsheets from Google Drive: {str(load_error)}")
                # Return existing data if available, rather than empty array
                existing_data = self.settings.get("available_spreadsheets", [])
                print(f"🔄 Returning existing data: {len(existing_data)} spreadsheets")
                return existing_data

        except Exception as e:
            print(f"❌ Error in refresh_spreadsheets: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return existing data instead of empty array
            existing_data = self.settings.get("available_spreadsheets", [])
            return existing_data