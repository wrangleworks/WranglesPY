"""
Connector for SSH
"""
from fabric import Connection as _Connection


_schema = {}

def run(host: str, user: str, command: str, password: str = None, key_filename: str = None) -> None:
    """
    Execute a command over ssh

    :param host: Domain or IP for the server
    :param user: User to connect as
    :param password: Password for the user
    :param key_filename: File that contains the private key
    :param command: Command or list of commands to execute
    """
    # If user has passed a single command, convert to a list of one
    if isinstance(command, str): command = [command]

    if password is not None:
        connect_kwargs = {'password': password}
    elif key_filename is not None:
        connect_kwargs = {'key_filename': key_filename}
    else:
        raise ValueError('A password or private key is required for the SSH connection')

    # Establish connection and run all the commands
    with _Connection(host, user=user, connect_kwargs=connect_kwargs) as conn:
        for ssh_command in command:
            conn.run(ssh_command)

_schema['run'] = """
type: object
description: Issue commands over SSH
required:
  - host
  - user
  - password
  - command
properties:
  host:
    type: string
    description: Domain or IP of the host
  user:
    type: string
    description: The user to connect as
  password:
    type: string
    description: Password for the user
  command:
    type:
      - string
      - array
    description: Command or list of commands to execute
"""