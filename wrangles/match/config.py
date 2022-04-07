import os

server = 'sql.wrangle.works'
database = 'Wrangleworks'
username = os.environ["USER"]
password = os.environ["PASSWORD"]

connection_string = 'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password