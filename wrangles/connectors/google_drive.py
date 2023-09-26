
# Google APIs
from googleapiclient.discovery import build as _build
from googleapiclient.http import MediaIoBaseDownload as _MediaIoBaseDownload
from googleapiclient.http import MediaIoBaseUpload as _MediaIoBaseUpload
from google.oauth2 import service_account as _service_account

from wrangles.connectors import file as _file
import io as _io
import pandas as _pd
import re as _re

# More information regarding auth and keys
# https://developers.google.com/identity/protocols/oauth2/service-account
# be sure to also share the folder with the service account email address as Editor

def read(
        file_id: str,
        project_id: str,
        private_key_id: str,
        private_key: str,
        client_email: str,
        client_id: str,
        **kwargs
        ) -> _pd.DataFrame:
    """
    Read a file from Google Drive using a Service Account
    
    :param file_id: ID of the file that contains the desired data
    :param project_id: ID of the Google project
    :param private_key_id: Private key identification of the Google project
    :param private_key: Private key of the Google Project
    :param client_email: Email of the Service account (Project)
    :param client_id: Client ID of the Google Project
    """
    # Remove extra back slashed from private key
    private_key = _re.sub("\\\\n", "\\n", private_key)
    
    # Credentials information
    creds_dict = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": private_key_id,
        "private_key": private_key,
        "client_email": client_email,
        "client_id": client_id,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        }
    
    # Create the appropriate Google Service
    scope = ['https://www.googleapis.com/auth/drive']
    creds = _service_account.Credentials.from_service_account_info(
        info=creds_dict,
        scopes=scope,
        **kwargs
    )
    
    # Authenticate and construct service.
    service = _build(
       'drive',
        'v3',
        credentials=creds
        )
    
    # Determine the mimeType based on file metadata
    file_data = service.files().get(
        fileId=file_id,
        fields='*',
        supportsAllDrives=True,
    ).execute()
    

    # For sheets files
    if file_data['mimeType'] == 'application/vnd.google-apps.spreadsheet':
        file_mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        file_type = 'xlsx' # Only needed for sheets
    
        request = service.files().export_media(
            fileId=file_id,
            mimeType=file_mimeType,
            )
    
    # For Excel files
    elif file_data['mimeType'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        request = service.files().get_media(
            fileId=file_id,
        )
        
    # For csv files
    elif file_data['mimeType'] == 'text/csv':
        request = service.files().get_media(
            fileId=file_id,
        )
    
    # For JSON files
    elif file_data['mimeType'] == 'application/json':
        file_mimeType = ''
        request = service.files().get_media(
            fileId=file_id,
        )
    
    else:
        raise ValueError('File type not supported. File type must be: Google Sheets, Excel, CSV, or JSON.')

    # Downloading the files
    fh = _io.BytesIO()
    downloader = _MediaIoBaseDownload(fd=fh, request=request)
    done = False
    while not done:
        done = downloader.next_chunk()
    fh.seek(0)
    
    # file to pandas dataFrame
    response = _io.BytesIO(fh.read())
    if file_data['mimeType'] == 'application/vnd.google-apps.spreadsheet':
        df = _file.read(f"{file_data['name']}.{file_type}", file_object=response)
    else:
        df = _file.read(f"{file_data['name']}", file_object=response)

    return df
    
    
def write(
        df: _pd.DataFrame,
        folder_id: str,
        file_name: str,
        project_id: str,
        private_key_id: str,
        private_key: str,
        client_email: str,
        client_id: str,
        to_sheets: bool=False,
        **kwargs
        ) -> None:
    """
    Write a file to Google Drive using a Service Account
    
    :param df: Dataframe to upload
    :param folder_id: Folder Id where the file will be placed
    :param file_name: Name to give the file
    :param to_sheets: (Optional) Convert an Excel file to Sheets. Only for Excel Files
    :param project_id: ID of the Google project
    :param private_key_id: Private key identification of the Google project
    :param private_key: Private key of the Google Project
    :param client_email: Email of the Service account (Project)
    :param client_id: Client ID of the Google Project
    """
    # Remove extra back slashed from private key
    private_key = _re.sub("\\\\n", "\\n", private_key)
    
    # Credentials information
    creds_dict = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": private_key_id,
        "private_key": private_key,
        "client_email": client_email,
        "client_id": client_id,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        }
    
    # Create the appropriate Google Service
    scope = ['https://www.googleapis.com/auth/drive']
    creds = _service_account.Credentials.from_service_account_info(
        info=creds_dict,
        scopes=scope,
        **kwargs
    )
    
    # Authenticate and construct service.
    service = _build(
       'drive',
        'v3',
        credentials=creds
        )
        
    # write file in memory
    memory_file = _io.BytesIO()
    _file.write(df, name=file_name, file_object=memory_file)
    memory_file.seek(0, 0)
    
    file_type = file_name.split('.')[1]
    
    # Excel to Sheets
    if file_type in ['xlsx'] and to_sheets == True:
        
        mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }
        
    # Excel file
    elif file_type in ['xlsx'] and to_sheets == False:
        
        mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
            'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }

    # CSV file
    elif file_type in ['csv']:
        
        mime_type = 'application/vnd.google-apps.file'
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
            'mimeType': "application/csv",
        }
        
    # JSON file
    elif file_type in ['json']:
        
        mime_type = 'application/vnd.google-apps.file'
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
            'mimeType': "application/json",
        }
        
    else:
        raise ValueError('File type not supported. File type must be: Excel, CSV, or JSON.')
    
    # Uploading the file to drive
    media = _MediaIoBaseUpload(
        memory_file,
        mimetype=mime_type,
        resumable=True,
    )
    
    service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id',
    ).execute()

