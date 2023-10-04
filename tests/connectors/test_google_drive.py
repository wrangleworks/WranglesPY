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
    
def test_reading_file_path():
    reading_path = "Google Connector Data/Python Tests Do not Delete/Do_not_delete.xlsx"
    df = read(
        share_link=reading_path,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'



#
# write to a folder
#

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
    
def test_writing_file_path():
    """
    Write data using a path
    """
    folder_path = "Google Connector Data/Python Tests Do not Delete/Created Files (DELETE Files)"
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })
    file_info = write(
        df=data,
        share_link= folder_path,
        file_name='df_writing_path.json',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    assert isinstance(file_info['id'], str)
    