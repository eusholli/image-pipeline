from quart import Quart, render_template, websocket
import jsonpickle

import asyncio
import json

from common.imagebusutil import FrameDetails, ImagebusTopic  # noqa
from common.natsclient import create, subscribe_handler  # noqa


app = Quart(__name__)


@app.route("/")
async def index():
    return await render_template("index.html")


@app.route("/home")
async def home():
    return await render_template("index.html")


@app.route("/imageai")
async def imageai():
    return await render_template("imageai.html")


@app.route("/redaction")
async def redaction():
    return await render_template("redaction.html")


# Handle original

original_frameDetails = None
imageai_frameDetails = None
redacted_frameDetails = None


@app.websocket('/ws')
async def process_ws():

    global original_frameDetails, imageai_frameDetails, redacted_frameDetails

    while True:
        event = await websocket.receive()

        if (event == "original"):
            if (original_frameDetails):
                print("fetch original: ",
                      original_frameDetails["from"]["frame_reference"])
                await websocket.send(json.dumps(original_frameDetails))
                original_frameDetails = None
            else:
                await websocket.send("original")

        elif (event == "imageai"):
            if (imageai_frameDetails):
                print("fetch imageai: ",
                      imageai_frameDetails["to"]["frame_reference"])
                await websocket.send(json.dumps(imageai_frameDetails))
                imageai_frameDetails = None
            else:
                await websocket.send("imageai")

        elif (event == "redacted"):
            if (redacted_frameDetails):
                print("fetch redacted: ",
                      redacted_frameDetails["re"]["frame_reference"])
                await websocket.send(json.dumps(redacted_frameDetails))
                redacted_frameDetails = None
            else:
                await websocket.send("redacted")

    return


async def run(loop):

    async def receive_original(msg):

        global original_frameDetails
        print("receive_original")
        data = msg.data.decode("utf-8")
        frame = jsonpickle.decode(data)
        original_frameDetails = {"type": "original",
                                 "from": frame.createResponse()}
        print("receive_original: ",
              original_frameDetails["from"]["frame_reference"])

    async def receive_imageai(msg):

        global imageai_frameDetails
        print("receive_imageai")
        data = msg.data.decode("utf-8")
        frame = jsonpickle.decode(data)
        imageai_frameDetails = {"type": "imageai",
                                "to": frame.createResponse()}
        print("receive_imageai: ",
              imageai_frameDetails["to"]["frame_reference"])

    async def receive_redacted(msg):

        global redacted_frameDetails
        print("receive_redacted")
        data = msg.data.decode("utf-8")
        frame = jsonpickle.decode(data)
        redacted_frameDetails = {"type": "redacted",
                                 "re": frame.createResponse()}
        print("receive_redacted: ",
              redacted_frameDetails["re"]["frame_reference"])

    nc = await create(loop)
    await nc.subscribe(ImagebusTopic.REDACTION_FRAME.name, cb=receive_redacted)
    await nc.subscribe(ImagebusTopic.IMAGEAI_FRAME.name, cb=receive_imageai)
    await nc.subscribe(ImagebusTopic.SOURCE_FRAME.name, cb=receive_original)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop))
    loop.run_until_complete(app.run(loop=loop, debug=True))
    try:
        loop.run_forever()
    finally:
        loop.close()
