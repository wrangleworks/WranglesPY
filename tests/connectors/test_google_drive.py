from wrangles.connectors.google_drive import read, write
import os
import pandas as _pd


# gather the credentials
project_id = os.getenv("GOOGLE_PROJECT_ID", "...")
private_key_id = os.getenv("GOOGLE_PRIVATE_KEY_ID", "...")
private_key = os.getenv("GOOGLE_PRIVATE_KEY", "...")
client_email = os.getenv("GOOGLE_CLIENT_EMAIL", "...")
client_id = os.getenv("GOOGLE_CLIENT_ID", "...")


def test_basic_read_id():
    read_file_id = "11QLHUhnrNCRJLCARqurneAceXqlWh301" # .xlsx file
    df = read(
        file=read_file_id,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'
def test_basic_read_link():
    """
    Link obtained from the share button
    """
    read_file_id = "https://docs.google.com/spreadsheets/d/1q6nPa-iKJ4u8ezT59K3vp9ukSafzNce1/edit?usp=sharing&ouid=105051950944307201734&rtpof=true&sd=true" # .xlsx file
    df = read(
        file=read_file_id,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'

def test_basic_read_url_link():
    """
    Link obtained from the url
    """
    read_file_id = "https://docs.google.com/spreadsheets/d/1q6nPa-iKJ4u8ezT59K3vp9ukSafzNce1/edit#gid=225914639" # .xlsx file
    df = read(
        file=read_file_id,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'
    
def test_reading_csv_file():
    """
    Link obtained from share button
    """
    read_file_id = "https://drive.google.com/file/d/1bohcPdc2RcK0OE_XDg2DzCgPFy-VKEOa/view?usp=sharing" # .csv file
    df = read(
        file=read_file_id,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id
    )
    assert df.iloc[106][2] == 'MEX'
    
def test_reading_json_file():
    """
    Link obtained from share button
    """
    read_file_id = "https://drive.google.com/file/d/15VOuxdYEPtLN6f-OCsi30QHNghGoxSa7/view?usp=sharing" # .json file
    df = read(
        file=read_file_id,
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
        file=reading_path,
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

# from share button
folder_share_link = "https://drive.google.com/drive/folders/1v_gmRNQV918rb0rCOVHYQDJrIdtW6xCl?usp=sharing"


def test_basic_write_to_sheets():
    """
    Write a data to a google sheets
    """
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })

    write(
        df=data,
        file= folder_share_link,
        # file= my_drive,
        file_name='df_to_sheets.gsheet',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    assert 1

def test_write_to_drive_xlsx():
    """
    Write data to an excel file in google drive
    """
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })

    write(
        df=data,
        file= folder_share_link,
        file_name='df_to_sheets.xlsx',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    assert 1
    
def test_write_to_drive_csv():
    """
    Write data to a csv file in google drive
    """
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })

    write(
        df=data,
        file= folder_share_link,
        file_name='df_to_sheets.csv',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    assert 1
    
def test_write_to_drive_json():
    """
    Write data to a json file in google drive
    """
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })

    write(
        df=data,
        file= folder_share_link,
        file_name='df_to_sheets.json',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    assert 1
    
def test_writing_file_path():
    """
    Write data using a folder path
    """
    folder_path = "Google Connector Data/Python Tests Do not Delete/Created Files (DELETE Files)"
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })
    write(
        df=data,
        file= folder_path,
        file_name='df_writing_path.json',
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    assert 1
    
def test_writing_file_path_with_file():
    """
    Writing data using a path with a file at the end
    """
    folder_path = "PyTest/Created Files (Can Be Deleted, Created Automatic)/df_writing_path2.xlsx"
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })
    write(
        df=data,
        file= folder_path,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    
    assert 1
    
def test_writing_file_share_link():
    """
    Writing to a file with a share link
    """
    file_link = "https://docs.google.com/spreadsheets/d/1YwSeSQWcVHTTPSBiMG3tfV_uJznhkSxqvUyylVMDQi8/edit?usp=drive_link"
    data = _pd.DataFrame({
        'col1': [1,2,3],
        'col2': [4,5,6]
    })
    write(
        df=data,
        file= file_link,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
    )
    assert 1
    

    
    