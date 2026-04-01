import pytest
from wrangles.connectors.ssh import run

def test_run_ssh(mocker):
    m = mocker.patch("fabric.Connection.run")
    m.return_value = 'test'
    config = {
        'host': 'wrangles',
        'user': 'mario', 
        'command': 'self_destruct',
        'password': '1234',
        'key_filename': 'secrets_file',
        'private_key': 'key'
    }
    assert run(**config) == None
    
# No password
def test_run_ssh_2(mocker):
    m = mocker.patch("fabric.Connection.run")
    m.return_value = 'test'
    config = {
        'host': 'wrangles',
        'user': 'mario', 
        'command': 'self_destruct',
        'key_filename': 'secrets_file',
        'private_key': 'key'
    }
    assert run(**config) == None
    
# No password and no key_filename
def test_run_ssh_3(mocker):
    m = mocker.patch("fabric.Connection.run")
    m.return_value = 'test'
    m2 = mocker.patch("paramiko.RSAKey.from_private_key")
    m2.return_value = 'test'
    config = {
        'host': 'wrangles',
        'user': 'mario', 
        'command': 'self_destruct',
        'private_key': 'key'
    }
    assert run(**config) == None
    
    
# Password is required error
def test_run_ssh_4(mocker):
    m = mocker.patch("fabric.Connection.run")
    m.return_value = 'test'
    config = {
        'host': 'wrangles',
        'user': 'mario', 
        'command': 'self_destruct',
    }
    with pytest.raises(ValueError) as info:
        run(**config)
    assert info.typename == 'ValueError' and info.value.args[0] == 'A password or private key is required for the SSH connection'