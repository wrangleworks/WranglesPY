"""
Send notifications to a varity of services
"""
import apprise as _apprise
from typing import Union as _Union


_schema = {}


def run(
    url: str,
    title: str,
    body: str,
    attachment: _Union[str, list] = None
):
    r"""
    Send a generic apprise notification.

    :param url: Apprise notification url. See https://github.com/caronc/apprise
    :param title: The title of the notification
    :param body: The body of the notification
    :param attachment: A file path & name to attach to the message. Supports a single file or a list of files. Must be supported by the specific notification type.
    """
    app_object = _apprise.Apprise()
    app_object.add(url)
    app_object.notify(
       body,
       title,
       attach=attachment
    )

_schema['run'] = """
type: object
description: Send a notification
required:
  - url
  - title
  - body
properties:
  url:
    type: string
    description: Apprise notification url. See https://github.com/caronc/apprise
  title:
    type: string
    description: The title of the notification
  body:
    type: string
    description: The body of the notification
  attachment:
    type:
      - string
      - array
    description: >-
      A file path & name to attach to the message.
      Supports a single file or a list of files.
      Must be supported by the specific notification type.
"""


class telegram():
  """
  Send telegram messages
  """
  _schema = {
    "run": """
      type: object
      description: Send a telegram message. See https://core.telegram.org/bots
      required:
        - bot_token
        - chat_id
        - title
        - body
      properties:
        bot_token:
          type: string
          description: The token for the bot. See https://core.telegram.org/bots
        chat_id:
          type: string
          description: The ID of the chat. See https://core.telegram.org/bots
        title:
          type: string
          description: The title of the notification
        body:
          type: string
          description: The body of the notification
        attachment:
          type:
            - string
            - array
          description: >-
            A file path & name to attach to the message.
            Supports a single file or a list of files.
            Must be supported by the specific notification type.
    """
  }

  def run(
    bot_token: str,
    chat_id: str,
    title: str,
    body: str,
    attachment: _Union[str, list] = None
  ):
    """
    Send a telegram notification

    See: https://core.telegram.org/bots

    :param bot_token: The token for the bot
    :param chat_id: The ID of the chat
    :param title: The title of the message
    :param body: The body of the message
    :param attachment: A file path & name to attach to the message. Supports a single file or a list of files. Must be supported by the specific notification type.
    """
    url = f"tgram://{bot_token}/{chat_id}/"
    run(url, title, body, attachment)


class email():
  """
  Send emails
  """
  _schema = {
    "run": """
      type: object
      description: Send an email
      required:
        - user
        - password
        - subject
        - body
      properties:
        user:
          type: string
          description: The user to send the email from. This may be your full email address, but depends on your service
        password:
          type: string
          description: The password for the user to send from
        subject:
          type: string
          description: The subject of the email
        body:
          type: string
          description: The body of the notification
        host:
          type: string
          description: The SMTP server for your service. This may be omitted for common services such as yahoo, gmail or hotmail but will be needed otherwise.
        to:
          type:
            - string
            - array
          description: An email or list of emails to send the email to. If omitted, the email will be sent to the sender.
        cc:
          type:
            - string
            - array
          description: An email or list of emails to cc the email to.
        bcc:
          type:
            - string
            - array
          description: Blind Carbon Copy email address(es).
        name: 
          type: string
          description: The name to show the email as being from. If omitted, defaults to the user.
        domain:
          type: string
          description: The domain to send the email under. If omitted, it will be inferred from the user
        attachment:
          type:
            - string
            - array
          description: >-
            A file path & name to attach to the message.
            Supports a single file or a list of files.
            Must be supported by the specific notification type.
    """
  }

  def run(
    user: str,
    password: str,
    subject: str,
    body: str,
    to: _Union[str, list] = None,
    cc: _Union[str, list] = None,
    bcc: _Union[str, list] = None,
    domain: str = None,
    host: str = None,
    name: str = None,
    attachment: _Union[str, list] = None
  ):
    """
    Send an email

    :param user: The user to send the email from. This may be your full email address, but depends on your service
    :param password: The password for the user to send from
    :param subject: The subject of the email
    :param body: The body of the email
    :param to: An email or list of emails to send the email to. If omitted, the email will be sent to the sender.
    :param cc: An email or list of emails to cc the email to.
    :param bcc: Blind Carbon Copy email address(es).
    :param domain: The domain to send the email under. If omitted, it will be inferred from the user
    :param host: The SMTP server for your service. This may be omitted for common services such as yahoo, gmail or hotmail but will be needed otherwise.
    :param name: The name to show the email as being from. If omitted, defaults to the user.
    :param attachment: A file path & name to attach to the message. Supports a single file or a list of files. Must be supported by the specific notification type.
    """
    # Construct the Apprise URL.
    if user.split('@')[-1] in ['yahoo.com', 'hotmail.com', 'live.com', 'gmail.com', 'fastmail.com']:
        # Handle apprise built in structured domains
        url = f"mailto://{user.split('@')[0]}:{password}@{user.split('@')[1]}?format=text"
    else:
        if domain:
            url = f"mailtos://{domain}?format=text&user={user.replace('@', '%40')}&pass={password}"
        else:
            url = f"mailtos://{user.split('@')[-1]}?format=text&user={user.replace('@', '%40')}&pass={password}"

    # Add optional components to the url
    url = url + f"&name={name or user.replace('@', '%40')}"

    if host:
        url = url + f"&smtp={host}"

    if to:
        if isinstance(to, str): to = [to]
        url = url + f"&to={','.join(to)}".replace('@', '%40')

    if cc:
        if isinstance(cc, str): cc = [cc]
        url = url + f"&cc={','.join(cc)}".replace('@', '%40')

    if bcc:
        if isinstance(bcc, str): bcc = [bcc]
        url = url + f"&bcc={','.join(bcc)}".replace('@', '%40')

    run(url, subject, body, attachment)
    
    
class slack():
  """
  Send Slack Messages
  """
  _schema = {
  "run": """
    type: object
    description: Send a message to Slack
    required:
      - web_hook
      - title
      - message
    properties:
      web_hook:
        type: string
        description: Webhook to post a message to Slack
      title:
        type: string
        description: Title of the message to send to Slack
      message:
        type: string
        description: Message to send to Slack
      attachment:
        type:
          - string
          - array
        description: >-
          A file path & name to attach to the message.
          Supports a single file or a list of files.
          Must be supported by the specific notification type.
  """  
  }
  
  def run(
      web_hook: str,
      title: str,
      message: str,
      attachment: _Union[str, list] = None
  ):
      # Apprise supports this Slack Webhook as-is (as of v0.7.7); 
      # you no longer need to parse the URL any further
      run(web_hook, title, message, attachment)
      
