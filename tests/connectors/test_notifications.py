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
    