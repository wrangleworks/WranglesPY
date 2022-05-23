"""
Connector for SSH
"""
from fabric import Connection


_schema = {}

def execute(host: str, user: str, password: str, command: str) -> None:
    """
    Execute a command over ssh
    """
    Connection(host, user=user, connect_kwargs={'password': password}).run(command)

_schema['execute'] = """
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
    type: string
    description: Command to send
"""