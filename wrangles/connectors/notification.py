import apprise


_schema = {}


def run(url: str, title: str, body: str):
    app_object = apprise.Apprise()
    app_object.add(url)
    app_object.notify(body, title)

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
"""