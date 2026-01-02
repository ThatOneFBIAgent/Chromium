import json
import io
import tempfile
from typing import Optional
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from config import shared_config
from utils.logger import get_logger

log = get_logger()

class DriveManager:
    def __init__(self):
        self.creds_dict = shared_config.get_drive_creds()
        self.folder_id = shared_config.DRIVE_FOLDER_ID
        self.service = None
        # Note: initialize_service is now called lazily on first use, not at import time

    def initialize_service(self):
        if self.service:
            return

        if self.creds_dict:
            try:
                # Check if it's a Service Account or User Token
                if 'type' in self.creds_dict and self.creds_dict['type'] == 'service_account':
                    creds = service_account.Credentials.from_service_account_info(
                        self.creds_dict,
                        scopes=['https://www.googleapis.com/auth/drive.file']
                    )
                else:
                    # Assume User Credentials (token.json format)
                    creds = Credentials.from_authorized_user_info(
                        self.creds_dict,
                        scopes=['https://www.googleapis.com/auth/drive.file']
                    )
                    
                # Refresh if needed (for User Creds mostly)
                if creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        log.network("Refreshed Drive OAuth token.")
                    except Exception as e:
                        log.error(f"Failed to refresh Drive token", exc_info=e)
                        
                self.service = build('drive', 'v3', credentials=creds)
                log.network("Google Drive service initialized.")
            except Exception as e:
                log.error("Failed to initialize Google Drive service", exc_info=e)

    def upload_file(self, filename: str, content: int | str | bytes, mimetype: str = 'text/plain') -> Optional[str]:
        """
        Uploads content as a file to Google Drive. Returns the webViewLink or None.
        Content can be str (utf-8) or bytes.
        """
        self.initialize_service()
        if not self.service or not self.folder_id:
            return None

        try:
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            
            # Create a bytes IO stream
            if isinstance(content, str):
                fh = io.BytesIO(content.encode('utf-8'))
            else:
                fh = io.BytesIO(content)
                
            media = MediaIoBaseUpload(fh, mimetype=mimetype, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            log.network(f"Uploaded file {filename} to Drive. ID: {file.get('id')}")
            return file.get('webViewLink')
            
        except Exception as e:
            log.error(f"Failed to upload to Drive", exc_info=e)
            return None

    def find_file(self, filename: str) -> Optional[str]:
        """Finds a file by name in the configured folder. Returns file_id or None."""
        self.initialize_service()
        if not self.service or not self.folder_id:
            return None

        try:
            # Query for exact name match in the specific folder, not trashed
            query = f"name = '{filename}' and '{self.folder_id}' in parents and trashed = false"
            results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            items = results.get('files', [])
            
            if not items:
                return None
            return items[0]['id']
            
        except Exception as e:
            log.error(f"Failed to search file on Drive", exc_info=e)
            return None

    def update_file(self, file_id: str, content: int | str | bytes, mimetype: str = 'text/plain') -> Optional[str]:
        """Updates an existing file's content."""
        self.initialize_service()
        if not self.service:
            return None
            
        try:
            # Create a bytes IO stream
            if isinstance(content, str):
                fh = io.BytesIO(content.encode('utf-8'))
            else:
                fh = io.BytesIO(content)
                
            media = MediaIoBaseUpload(fh, mimetype=mimetype, resumable=True)
            
            file = self.service.files().update(
                fileId=file_id,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            log.network(f"Updated file ID {file_id} on Drive.")
            return file.get('webViewLink')
            
        except Exception as e:
            log.error(f"Failed to update file on Drive", exc_info=e)
            return None

    def download_file(self, file_id: str) -> Optional[bytes]:
        """Downloads a file's content by ID."""
        self.initialize_service()
        if not self.service:
            return None
            
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
            return fh.getvalue()
            
        except Exception as e:
            log.error(f"Failed to download file from Drive", exc_info=e)
            return None

    def debug_list_files(self, limit: int = 10):
        """Lists files in the configured folder to debug visibility."""
        self.initialize_service()
        if not self.service or not self.folder_id:
            return
            
        try:
            query = f"'{self.folder_id}' in parents and trashed = false"
            results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)', pageSize=limit).execute()
            items = results.get('files', [])
            
            log.network(f"DEBUG: Found {len(items)} files in folder {self.folder_id}:")
            for item in items:
                log.network(f" - {item['name']} ({item['id']})")
                
        except Exception as e:
            log.error(f"Failed to debug list files", exc_info=e)

# Global instance
drive_manager = DriveManager()
