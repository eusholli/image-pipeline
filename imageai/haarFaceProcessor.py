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


configPath = os.path.join(
    sys.path[0], 'ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt')
weightsPath = os.path.join(sys.path[0], 'frozen_inference_graph.pb')

face_cascade = cv2.CascadeClassifier(os.path.join(
    sys.path[0], 'haarcascade_frontalface_default.xml'))


async def analyzeImages(nc, frameDetails, parent):
    """
    Start analyzing images
    """
    print("Start analyzing images...")

    try:
        frameReference = 0
        totalAnalysisTime = 0

        frameReference += 1
        byteStream = io.BytesIO(parent.image)
        originalTime = parent.dateTime
        image = np.asarray(bytearray(byteStream.read()), dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_UNCHANGED)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        beforeDetection = time.process_time()
        # imageai_frame, detection = detector.detectObjectsFromImage(
        #     input_image=image, input_type="array", output_type="array"
        # )
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        detectionTime = time.process_time() - beforeDetection
        totalAnalysisTime += detectionTime
        imageTime = datetime.datetime.now()

        print("--------------------------------")

        identified_objects = []

        if len(faces) != 0:
            for (x, y, w, h) in faces:
                label = 'face'
                confidence = 1.00
                box = [x, y, w, h]
                print(
                    label,
                    " : ",
                    confidence,
                    " : ",
                    box,
                )
                identified_objects.append(
                    {
                        "name": label,
                        "percentage_probability": round(confidence*100, 2),
                        "position": [
                            int(box[0]),
                            int(box[1]),
                            int(box[2]),
                            int(box[3]),
                        ],
                    }
                )

                cv2.rectangle(image, box, color=(0, 255, 0), thickness=2)
                annotate = label + ' - ' + str(round(confidence*100, 2))
                cv2.putText(image, annotate, (box[0]+10, box[1]+30),
                            cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
            print("--------------------------------\n\r")

        # Convert image to png
        ret, buffer = cv2.imencode(".jpg", image)

        frameDetails.setChildFrame(
            frameReference,
            buffer.tobytes(),
            identified_objects,
            parent,
            round(detectionTime, 2),
            round(totalAnalysisTime / frameReference, 2),
        )

        await nc.publish(frameDetails.topic, jsonpickle.encode(frameDetails).encode("utf-8"))
        await asyncio.sleep(.01)

    except Exception as e:
        traceback.print_exc()
        print("\nExiting.")


async def initiate(loop):
    """
    Producer will publish to Kafka Server a video file given as a system arg.
    Otherwise it will default by streaming webcam feed.
    """
    parser = argparse.ArgumentParser(
        prog="haarFaceProcessor",
        description="start image recognition on incoming frames",
    )
    parser.add_argument(
        "-t",
        "--topic",
        default=ImagebusTopic.IMAGEAI_FRAME.name,
        help="set the topic name for publishing the feed, defaults to "
        + ImagebusTopic.IMAGEAI_FRAME.name,
    )

    parser.add_argument(
        "-i",
        "--input",
        default=ImagebusTopic.SOURCE_FRAME.name,
        help="set the topic name for reading the incoming feed, defaults to "
        + ImagebusTopic.SOURCE_FRAME.name,
    )

    parser.add_argument(
        "-n",
        "--name",
        help='set the display name of this object detection process, defaults to "haarFaceProcessor" if missing',
        default="haarFaceProcessor",
    )

    args = parser.parse_args()

    nc = await create(loop)

    frameDetails = FrameDetails(name=args.name, topic=args.topic)

    async def receive_original(msg):

        global original_frameDetails
        print("receive_original")
        data = msg.data.decode("utf-8")
        frame = jsonpickle.decode(data)
        await analyzeImages(nc, frameDetails, frame)

    await nc.subscribe(ImagebusTopic.SOURCE_FRAME.name, cb=receive_original)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initiate(loop))
    loop.run_forever()
