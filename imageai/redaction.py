import traceback
import io
import numpy as np
import sys
import time
import cv2
import datetime
import jsonpickle
import argparse
import asyncio
import os


from common.imagebusutil import FrameDetails, ImagebusTopic  # noqa
from common.natsclient import create, subscribe_handler  # noqa


async def redactImages(nc, frameDetails, redactedObjects, parent):
    """
    Start redacting images
    """
    print("Start redacting images...")

    # Black color in BGR
    color = (0, 0, 0)
    # Line thickness of 2 px
    thickness = -1

    try:
        frameReference = 0
        totalAnalysisTime = 0

        frameReference += 1
        byteStream = io.BytesIO(parent.image)
        originalTime = parent.dateTime
        image = np.asarray(bytearray(byteStream.read()), dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_UNCHANGED)

        beforeDetection = time.process_time()

        print("--------------------------------")

        details = parent.details
        for eachObject in details:
            object_type = eachObject["name"]

            if object_type in redactedObjects:
                eachObject["redacted"] = True
                eachObject["name"] = "REDACTED"
                print(object_type + " to be redacted...")
                start_point = (
                    eachObject["position"][0],
                    eachObject["position"][1],
                )
                end_point = (
                    eachObject["position"][2],
                    eachObject["position"][3],
                )
                cv2.rectangle(image, eachObject["position"], color=(
                    0, 0, 0), thickness=-1)
                # image = cv2.rectangle(image, start_point, end_point, color, thickness)

        print("--------------------------------\n\r")

        detectionTime = time.process_time() - beforeDetection
        totalAnalysisTime += detectionTime

        # Convert image to png
        ret, buffer = cv2.imencode(".jpg", image)

        frameDetails.setChildFrame(
            frameReference,
            buffer.tobytes(),
            details,
            parent,
            round(detectionTime, 4),
            round(totalAnalysisTime / frameReference, 4),
        )

        await nc.publish(frameDetails.topic, jsonpickle.encode(frameDetails).encode("utf-8"))
        await asyncio.sleep(.01)

    except Exception as e:
        traceback.print_exc()
        print("\nExiting.")
        sys.exit(1)


async def initiate(loop):
    """
    Producer will publish to Kafka Server a video file given as a system arg.
    Otherwise it will default by streaming webcam feed.
    """
    parser = argparse.ArgumentParser(
        prog="redaction", description="start redacting incoming frames"
    )

    parser.add_argument(
        "redactedObjects",
        nargs="*",
        help="list of objects to be redacted ex. person cup",
        default=["person"],
    )

    parser.add_argument(
        "-t",
        "--topic",
        default=ImagebusTopic.REDACTION_FRAME.name,
        help="set the topic name for publishing the feed, defaults to "
        + ImagebusTopic.REDACTION_FRAME.name,
    )

    parser.add_argument(
        "-i",
        "--input",
        default=ImagebusTopic.IMAGEAI_FRAME.name,
        help="set the topic name for reading the incoming feed, defaults to "
        + ImagebusTopic.IMAGEAI_FRAME.name,
    )

    parser.add_argument(
        "-n",
        "--name",
        help='set the display name of this redaction process, defaults to "redactionProcessor" if missing',
        default="redactionProcessor",
    )

    args = parser.parse_args()
    print(args.redactedObjects)

    nc = await create(loop)

    frameDetails = FrameDetails(name=args.name, topic=args.topic)

    async def receive_original(msg):

        global original_frameDetails
        print("receive_original")
        data = msg.data.decode("utf-8")
        frame = jsonpickle.decode(data)
        await redactImages(nc, frameDetails, args.redactedObjects, frame)

    await nc.subscribe(ImagebusTopic.IMAGEAI_FRAME.name, cb=receive_original)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initiate(loop))
    loop.run_forever()
