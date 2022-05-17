"""
Connector for SSH
"""
from fabric import Connection


def execute(host: str, user: str, password: str, command: str) -> None:
    """
    Execute a command over ssh
    """
    Connection(host, user=user, connect_kwargs={'password': password}).run(command)
