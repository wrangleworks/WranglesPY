import apprise
import wrangles
import pandas as pd

from wrangles.connectors.notification import run
def test_notifications(mocker):
    m = mocker.patch("apprise.Apprise")
    m.notify.return_value = 'Message Sent!'
    config = {
        'url': 'test',
        'title': 'test',
        'body': 'Message Test!'
    }
    # function return None
    assert run(**config) == None
    
from wrangles.connectors.notification import telegram
def test_telegram(mocker):
    config = {
        'bot_token': '1234',
        'chat_id': '1234',
        'title': 'Msg Title',
        'body': 'Hello Wrangles',
    }
    assert telegram.run(**config) == None
 
from wrangles.connectors.notification import email
def test_email(mocker):
    config = {
        'user': 'mario@email.com',
        'password': '1234',
        'subject': 'Test Email',
        'body': 'Wrangles are cool!',
        'to': 'wrangles@email.com',
        'cc': 'fey@email.com',
        'domain': 'email'
    }
    assert email.run(**config) == None
    
# No domain
def test_email_2(mocker):
    config = {
        'user': 'mario@email.com',
        'password': '1234',
        'subject': 'Test Email',
        'body': 'Wrangles are cool!',
        'to': 'wrangles@email.com',
        'cc': 'fey@email.com',
    }
    assert email.run(**config) == None
    
# Common Domain
def test_email_2(mocker):
    config = {
        'user': 'mario@gmail.com',
        'password': '1234',
        'subject': 'Test Email',
        'body': 'Wrangles are cool!',
        'to': 'wrangles@email.com',
        'cc': 'fey@email.com',
    }
    assert email.run(**config) == None
    
from wrangles.connectors.notification import slack

def test_slack(mocker):
    config = {
        'web_hook': 'hook_here',
        'title': 'Wrangles',
        'message': 'Message about wrangles!'
    }
    assert slack.run(**config) == None
    
    