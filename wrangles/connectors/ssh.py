"""
Connector for SSH
"""
from typing import Union as _Union
from io import StringIO as _StringIO
import logging as _logging
from ..utils import LazyLoader as _LazyLoader

# Lazy load external dependencies
_fabric = _LazyLoader('fabric')
_paramiko = _LazyLoader('paramiko')


_schema = {}

def run(host: str, user: str, command: _Union[str, list], password: str = None, key_filename: str = None, private_key: str = None) -> None:
    """
    Execute a command over ssh

    :param host: Domain or IP for the server
    :param user: User to connect as
    :param password: Password for the user
    :param key_filename: File that contains the private key
    :param private_key: Provide an RSA Private Key as a string
    :param command: Command or list of commands to execute. When providing a list, note that all commands are executed in isolation, i.e. cd /dir in a prior command will not affect the directory for later commands.  
    """
    _logging.info(f": Executing SSH command :: {host}")

    # If user has passed a single command, convert to a list of one
    if isinstance(command, str): command = [command]

    if password is not None:
        connect_kwargs = {'password': password}
    elif key_filename is not None:
        connect_kwargs = {'key_filename': key_filename}
    elif private_key is not None:
        connect_kwargs = {
            'pkey': _paramiko.RSAKey.from_private_key(_StringIO(private_key))
        }
    else:
        raise ValueError('A password or private key is required for the SSH connection')

    # Establish connection and run all the commands
    with _fabric.Connection(host, user=user, connect_kwargs=connect_kwargs) as conn:
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
  key_filename:
    type: string
    description: Path to a file that contains the private key
  private_key:
    type: string
    description: Provide an RSA Private Key as a string
  command:
    type:
      - string
      - array
    description: Command or list of commands to execute. When providing a list, note that all commands are executed in isolation, i.e. cd /dir in a prior command will not affect the directory for later commands.
"""
