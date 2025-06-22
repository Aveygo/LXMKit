# LXMKit

A stupid simple toolkit to build & host Nomadnet bots

```python
from LXMKit.app import LXMFApp, Message
from LXMKit.mu import Micron, Paragraph

import RNS

app = LXMFApp(app_name="demo")

@app.request_handler("/page/index.mu")
def sample(path:str, link:RNS.Link):
    return Micron([
        Paragraph("Hello World!")
    ])

@app.delivery_callback
def delivery_callback(message: Message):
    if message.content == "ping":
        message.author.send("pong")

if __name__ == "__main__":
    app.run()
```

