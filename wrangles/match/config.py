import os
import platform

server = 'sql.wrangle.works'
database = 'Wrangleworks'
username = os.environ.get("USER", '')
password = os.environ.get("PASSWORD", '')

if platform.system() == 'Windows':
    driver = "SQL Server"
elif platform.system() == 'Linux':
    driver = "ODBC Driver 17 for SQL Server"

connection_string = 'DRIVER={' + driver + '};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password