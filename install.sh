#!/bin/bash -x

virtualenv venv

echo 'export PYTHONPATH="${PWD}"' >>  venv/bin/activate
. venv/bin/activate

pip install asyncio-nats-client jsonpickle quart opencv-contrib-python

# imageai https://github.com/ankityddv/ObjectDetector-OpenCV
# nothing extra to install



