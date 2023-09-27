from wrangles.connectors.google_drive import read, write
import os
import pandas as _pd


# gather the credentials
project_id = os.getenv("GOOGLE_PROJECT_ID", "...")
private_key_id = os.getenv("GOOGLE_PRIVATE_KEY_ID", "...")
private_key = os.getenv("GOOGLE_PRIVATE_KEY", "...")
client_email = os.getenv("GOOGLE_CLIENT_EMAIL", "...")
client_id = os.getenv("GOOGLE_CLIENT_ID", "...")

from google.oauth2 import service_account as _service_account
from googleapiclient.discovery import build as _build
import re as _re
# function to delete files after they are created
def delete_file_in_drive(file_id_or_link):
    creds_dict = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": private_key_id,
        "private_key": _re.sub("\\\\n", "\\n", private_key), # Remove extra back slashed from private key
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
    )

    # Authenticate and construct service.
    service = _build(
        'drive',
        'v3',
        credentials=creds
        )

    # Extract the file ID from the file path or link
    file_id = None

    # If it's a link, extract the file ID from the link
    if 'drive.google.com' in file_id_or_link:
        parts = file_id_or_link.split('/')
        for i, part in enumerate(parts):
            if part == 'd':
                file_id = parts[i + 1]
                break

    # If it's a file ID, use it directly
    if not file_id and file_id_or_link.startswith('file/d/'):
        file_id = file_id_or_link[len('file/d/'):]
        

    try:
        service.files().delete(fileId=file_id).execute()
        print(f'File deleted: {file_id}')
    except:
        print(f'An Error occurred: {file_id} or file is already deleted')

def test_basic_read_id():
    read_file_id = "11QLHUhnrNCRJLCARqurneAceXqlWh301" # .xlsx file
    df = read(
        share_link=read_file_id,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'
    
def test_basic_read_link():
    read_file_id = "https://docs.google.com/spreadsheets/d/11QLHUhnrNCRJLCARqurneAceXqlWh301/edit?usp=drive_link" # .xlsx file
    df = read(
        share_link=read_file_id,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'

def test_basic_read_url_link():
    read_file_id = "https://docs.google.com/spreadsheets/d/11QLHUhnrNCRJLCARqurneAceXqlWh301/edit#gid=225914639" # .xlsx file
    df = read(
        share_link=read_file_id,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'
    
def test_reading_csv_file():
    read_file_id = "https://drive.google.com/file/d/1LuPWzzlXNwpDUHmxYmYZ4fXXoUzCA0F9/view?usp=drive_link"
    df = read(
        share_link=read_file_id,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'
    
def test_reading_json_file():
    read_file_id = "https://drive.google.com/file/d/1lxybaNym4U3jf5nHhCd5hQH044Ucpa8t/view?usp=drive_link"
    df = read(
        share_link=read_file_id,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'


# write to a folder
folder_share_link = "https://drive.google.com/drive/folders/1a6AXyn-4PAqjaVJasr9WtQC7XY5k1G3Y?usp=drive_link"

def test_basic_write_to_sheets():
    """
    Write a data to a google sheets
    """
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })

    file_info = write(
        df=data,
        share_link= folder_share_link,
        file_name='df_to_sheets.gsheet',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    # the function return a dict with the file if
    assert isinstance(file_info['id'], str)

def test_write_to_drive_xlsx():
    """
    Write data to an excel file in google drive
    """
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })

    file_info = write(
        df=data,
        share_link= folder_share_link,
        file_name='df_to_sheets.xlsx',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    # the function return a dict with the file if
    assert isinstance(file_info['id'], str)
    
def test_write_to_drive_csv():
    """
    Write data to a csv file in google drive
    """
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })

    file_info = write(
        df=data,
        share_link= folder_share_link,
        file_name='df_to_sheets.csv',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    # the function return a dict with the file if
    assert isinstance(file_info['id'], str)
    
def test_write_to_drive_json():
    """
    Write data to a json file in google drive
    """
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })

    file_info = write(
        df=data,
        share_link= folder_share_link,
        file_name='df_to_sheets.json',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    # the function return a dict with the file if
    assert isinstance(file_info['id'], str)
    