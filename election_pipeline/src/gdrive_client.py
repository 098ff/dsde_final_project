import os
import io
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_gdrive_service():
    """สร้าง Service Object โดยใช้ Token หากไม่มีให้ Auth ใหม่"""
    creds = None
    if os.path.exists('credentials/token.json'):
        creds = Credentials.from_authorized_user_file('credentials/token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials/client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('credentials/token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def list_folders_in_folder(service, parent_folder_id, folder_name=None):
    """ค้นหาโฟลเดอร์ลูก (รองรับการหาชื่อบางส่วนแบบ Contains)"""
    query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    
    if folder_name:
        query += f" and name contains '{folder_name}'"
        
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

def download_files_from_folder(service, folder_id, download_dir):
    """ดาวน์โหลด PDF ทั้งหมดในโฟลเดอร์หน่วยเลือกตั้งมาไว้ใน Local Temp"""
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    downloaded_paths = []
    os.makedirs(download_dir, exist_ok=True)
    
    for file in files:
        request = service.files().get_media(fileId=file['id'])
        file_path = os.path.join(download_dir, file['name'])
        fh = io.FileIO(file_path, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        downloaded_paths.append(file_path)
        
    return downloaded_paths