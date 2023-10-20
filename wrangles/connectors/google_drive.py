
# Google APIs
from googleapiclient.discovery import build as _build
from googleapiclient.http import MediaIoBaseDownload as _MediaIoBaseDownload
from googleapiclient.http import MediaIoBaseUpload as _MediaIoBaseUpload
from google.oauth2 import service_account as _service_account

from wrangles.connectors import file as _file
import io as _io
import pandas as _pd
import re as _re

_schema = {}

# More information regarding auth and keys
# https://developers.google.com/identity/protocols/oauth2/service-account
# be sure to also share the folder with the service account email address as Editor

def _get_id_from_path(service, path, type):
    """
    Get the file ID from the the path provided
    """
    path_list = path.split("/")
    folder_list = path_list[:-1]
    if type == 'read':
        file = _re.search(r'(\w+)\.(xlsx|csv|gsheet|json)', path)[0]
    
    # get the root folder id from the path
    query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_list[0]}' and trashed = false"
    results = service.files().list(q=query, fields="files(id)", supportsAllDrives=True,  includeItemsFromAllDrives=True).execute()
    if results['files'] == []:
        raise ValueError(f"Folder '{folder_list[0]}' does not exist in Google Drive or does not have the correct Service Account permissions.""")
    root_id = results['files'][0]['id']
    
    # Build the id_stack to keep track of folder ids
    id_stack = root_id # initialize with the root folder id
    file_id = ""
    
    # iterate through the path
    for part in path_list[1:]:
        
        # Check if part is the last element in the list
        if part == path_list[-1] and type == 'read':
            # search for a file using the id_stack
            query = f"'{id_stack}' in parents and mimeType != 'application/vnd.google-apps.folder'"
            results = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True,  includeItemsFromAllDrives=True).execute()
            
            # check if the file exists in last folder in the path
            if [x['name'] for x in results['files'] if x['name'] == file]:
                file_id = [x['id'] for x in results['files'] if x['name'] == file][0]
                return file_id
            
        elif part == path_list[-1] and type == 'write':
            query = f"'{id_stack}' in parents and mimeType = 'application/vnd.google-apps.folder'"
            results = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True,  includeItemsFromAllDrives=True).execute()
            
            # check if the file exists in last folder in the path and get id
            if [x['name'] for x in results['files'] if x['name'] == part]:
                file_id = [x['id'] for x in results['files'] if x['name'] == part][0]
                return file_id
        
        else:
            # Keep iterating through the path/folders. using the folder id, check that the folder contains the sub folder
            query = f"'{id_stack}' in parents and mimeType = 'application/vnd.google-apps.folder'"
            results = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True,  includeItemsFromAllDrives=True).execute()
            
            # check if the sub folder exists in the current folder
        if [x['name'] for x in results['files'] if x['name'] == part]:
            # update the id_stack
            id_stack = [x['id'] for x in results['files'] if x['name'] == part][0]
    
    return None # if nothing is found


def read(
        file: str,
        project_id: str,
        private_key_id: str,
        private_key: str,
        client_email: str,
        client_id: str,
        **kwargs
        ) -> _pd.DataFrame:
    """
    Read a file from Google Drive using a Service Account
    
    :param file: ID of the file that contains the desired data or the sharable link or the file path
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
    
    # check if user provided sharable link or file id
    if 'drive.google.com' in file or 'docs.google.com' in file:
        parts = file.split('/')
        for i, part in enumerate(parts):
            if part == 'd':
                file_id = parts[i + 1]
                break
    
    # check if the share link is a path
    elif '/' in file and 'https://' not in file:
        file_id = _get_id_from_path(service, file, 'read')
        if file_id == None:
            raise ValueError(f"Invalid path: '{file}'")
        
    # this is just the model id
    else :
        file_id = file
    
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
    elif file_data['mimeType'] == 'text/csv' or file_data['mimeType'] == 'application/csv':
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

_schema['read'] = """
type: object
description: Import data from a Google Drive file
required:
  - file
  - project_id
  - private_key_id
  - private_key
  - client_email
  - client_id
properties:
  file:
    type: string
    description: ID of the file that contains the desired data or the sharable link or the Drive file path
  project_id:
    type: string
    description: ID of the Google project
  private_key_id:
    type: string
    description: Private key identification of the Google project
  private_key:
    type: string
    description: Private key of the Google Project
  client_email:
    type: string
    description: Email of the Service account (Project)
  client_id:
    type: string
    description: Client ID of the Google Project
"""
    
def write(
        df: _pd.DataFrame,
        file: str,
        project_id: str,
        private_key_id: str,
        private_key: str,
        client_email: str,
        client_id: str,
        file_name: str = None,
        **kwargs
        ) -> None:
    """
    Write a file to Google Drive using a Service Account.
    Function returns a dictionary with the file ID.
    {'id': '12345ABCD'}
    
    :param df: Dataframe to upload
    :param file: Folder sharable link (File name required) or file sharable link or a file path
    :param file_name: (Optional except when using a folder share link or folder path) Name to give the file
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
    
    # user provided a folder sharable link
    if 'drive.google.com' in file:
        
        # file_name is required when using a folder share link
        if file_name == None:
            raise ValueError('file_name is required when using a folder share link.')
        
        parts = file.split('/')
        for i, part in enumerate(parts):
            if part == 'folders':
                folder_id = parts[i + 1]
                # check for any additional separators
                if '?' in folder_id:
                    folder_id = folder_id.split('?')[0]
                break
    
    # user provided a path with a file name
    elif '/' in file and 'https://' not in file:
        # if file_name is none, then extract the name from the path
        if file_name == None:
            file_name = file.split('/')[-1]
            # update the path to not include the file name
            file = '/'.join(file.split('/')[:-1])
        folder_id = _get_id_from_path(service, file, 'write')
        if folder_id == None:
            raise ValueError(f"Invalid path: '{file}'")
    
    # user provided a file sharable link -> use ID from link to make a quick update
    elif 'docs.google.com' in file:
        # get the file metadata from the link
        parts = file.split('/')
        for i, part in enumerate(parts):
            if part == 'd':
                folder_id = parts[i + 1]
                break
        # get the file_name from the id
        file_metadata = service.files().get(
            fileId=folder_id,
        ).execute()
        
        file_name = f"{file_metadata['name']}.xlsx"
        file_id = file_metadata['id']
        file_mime_type = file_metadata['mimeType']
        
        # write file in memory
        memory_file = _io.BytesIO()
        _file.write(df, name=file_name, file_object=memory_file)
        memory_file.seek(0, 0)
        # Uploading the file to drive
        media = _MediaIoBaseUpload(
            memory_file,
            mimetype=file_mime_type,
        )
        
        file = service.files().update(
            fileId=file_id,
            media_body=media,
        ).execute()
        
        return
    
    # user provided a folder id - should not be common
    else :
        folder_id = file
        
    # write file in memory
    memory_file = _io.BytesIO()
    # if file is gsheet, then write a temp xlsx file
    if file_name.split('.')[1] == 'gsheet':
        temp_tile = file_name.split('.')[0] + '.xlsx'
    else:
        temp_tile = file_name
    _file.write(df, name=temp_tile, file_object=memory_file)
    memory_file.seek(0, 0)
    
    file_type = file_name.split('.')[1]
    
    # Google Sheets
    if file_type in ['gsheet']:
        
        mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }
        
    # Excel file
    elif file_type in ['xlsx']:
        
        mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
            'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }

    # CSV file
    elif file_type in ['csv']:
        
        mime_type = 'text/csv'
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
            'mimeType': 'text/csv',
        }
        
    # JSON file
    elif file_type in ['json']:
        
        mime_type = 'application/json'
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
        # resumable=True,
    )
    
    # Check if the file already exists in folder
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='{file_name}'",
        fields="files(id)",
    ).execute()
    
    # if file exists, then replace it
    if results['files'] != []:
        file = service.files().update(
            fileId=results['files'][0]['id'],
            media_body=media,
        ).execute()
    else:
        # upload a new file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True,
        ).execute()
    
    return

_schema['write'] = """
type: object
description: Export data to a Google Drive file
required:
  - file
  - project_id
  - private_key_id
  - private_key
  - client_email
  - client_id
properties:
  file:
    type: string
    description: Folder sharable link (File name required) or file sharable link or a file path
  file_name:
    type: string
    description: (Optional except when using a folder share link or folder path) Name to give the file
  project_id:
    type: string
    description: ID of the Google project
  private_key_id:
    type: string
    description: Private key identification of the Google project
  private_key:
    type: string
    description: Private key of the Google Project
  client_email:
    type: string
    description: Email of the Service account (Project)
  client_id:
    type: string
    description: Client ID of the Google Project
"""