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

modelFile = os.path.join(
    sys.path[0], 'res10_300x300_ssd_iter_140000.caffemodel')
configFile = os.path.join(sys.path[0], 'deploy.prototxt.txt')

net = cv2.dnn.readNetFromCaffe(configFile, modelFile)

threshold = 0.4


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

        beforeDetection = time.process_time()
        # imageai_frame, detection = detector.detectObjectsFromImage(
        #     input_image=image, input_type="array", output_type="array"
        # )
        h, w = image.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
                                     (300, 300), (104.0, 117.0, 123.0))
        net.setInput(blob)
        faces = net.forward()

        detectionTime = time.process_time() - beforeDetection
        totalAnalysisTime += detectionTime
        imageTime = datetime.datetime.now()

        print("--------------------------------")

        identified_objects = []

        for i in range(faces.shape[2]):
            confidence = faces[0, 0, i, 2]
            if confidence > threshold:
                box = faces[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x, y, x1, y1) = box.astype("int")
                box = [x, y, x1, y1]

                print(
                    "face",
                    " : ",
                    confidence,
                    " : ",
                    box,
                )
                identified_objects.append(
                    {
                        "name": "face",
                        "percentage_probability": round(confidence*100, 2),
                        "position": [
                            int(box[0]),
                            int(box[1]),
                            int(box[2]),
                            int(box[3]),
                        ],
                    }
                )

                cv2.rectangle(image, (x, y), (x1, y1), (0, 255, 0), 4)
                annotate = str(round(confidence*100, 2))
                cv2.putText(image, annotate, (box[0]+10, box[1]+20),
                            cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 255, 0), 2)
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
        prog="dnnFaceProcessor",
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
        help='set the display name of this object detection process, defaults to "dnnFaceProcessor" if missing',
        default="dnnFaceProcessor",
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
