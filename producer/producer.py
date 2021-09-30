import argparse
import traceback
import cv2
import sys
import jsonpickle

import asyncio

from common.imagebusutil import FrameDetails, ImagebusTopic  # noqa
from common.natsclient import create, subscribe_handler  # noqa


async def publish_video(producer, frameDetails):
    """
    Publish given video file to a specified Kafka topic.
    Kafka Server is expected to be running on the localhost. Not partitioned.

    """
    # Open file
    video = cv2.VideoCapture(frameDetails.url)

    print("publishing media stream %s " % (frameDetails.url))

    frame_sample = frameDetails.frameRate

    count = 1
    while video.isOpened():
        if (frame_sample == 1):
            success, frame = video.read()
            count += 1

        else:
            while count % frame_sample != 0:
                count += 1
                success, frame = video.read()

            count += 1

        # Ensure file was read successfully
        if not success:
            print("bad read!")
            break

        # Convert image to png
        ret, buffer = cv2.imencode(".jpg", frame)
        frameDetails.setFrame(count, buffer.tobytes())

        # Convert to bytes and send to nats
        await producer.publish(frameDetails.topic, jsonpickle.encode(frameDetails).encode("utf-8"))
        await asyncio.sleep(0.01)
# producer.send(frameDetails.topic, frameDetails)

    #        time.sleep(0.2)

    video.release()
    print("publish complete")


async def publish_camera(producer, frameDetails):
    """
    Publish camera video stream to specified Kafka topic.
    Kafka Server is expected to be running on the localhost. Not partitioned.
    """

    print("publishing webcam...")

    camera = cv2.VideoCapture(0)
    try:
        frame_sample = frameDetails.frameRate
        count = 1
        while True:

            while count % frame_sample != 0:
                count += 1
                success, frame = camera.read()

            count += 1
            ret, buffer = cv2.imencode(".jpg", frame)
            frameDetails.setFrame(count, buffer.tobytes())

            await producer.publish(frameDetails.topic, jsonpickle.encode(frameDetails).encode("utf-8"))
            await asyncio.sleep(0.01)

            # Choppier stream, reduced load on processor
    #            time.sleep(3)

    except Exception as e:
        camera.release()
        traceback.print_exc()
        print("\nExiting.")


async def initiate(loop):
    """
    Producer will publish to Kafka Server a video file given as a system arg.
    Otherwise it will default by streaming webcam feed.
    """
    parser = argparse.ArgumentParser(
        prog="producer", description="start sampling a video source"
    )
    parser.add_argument(
        "source",
        help="the video source, either a media url(rtsp, rtmp) or special string 'webcam'",
        metavar="URL | WEBCAM",
    )

    parser.add_argument(
        "-f",
        "--frame",
        type=int,
        default="30",
        help='process "1 every VALUEth frame fetched"',
        metavar="VALUE",
    )

    parser.add_argument(
        "-n",
        "--name",
        help='set the display name of the video source, defaults to "source" if missing',
    )

    parser.add_argument(
        "-t",
        "--topic",
        default=ImagebusTopic.SOURCE_FRAME.name,
        help="set the topic name for publishing the feed, defaults to "
        + ImagebusTopic.SOURCE_FRAME.name,
    )

    args = parser.parse_args()
    print(args)
    frameDetails = FrameDetails(
        name=args.name, frameRate=args.frame, url=args.source, topic=args.topic
    )

    nc = await create(loop)

    if args.source.lower() == "webcam":
        await publish_camera(nc, frameDetails)
    else:
        await publish_video(nc, frameDetails)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initiate(loop))
    # loop.run_forever()
