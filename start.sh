#!/bin/bash

tput setaf 7
echo "Starting image-pipeline processes..."

echo "Starting Nats"
docker pull nats:latest
docker run -d --name nats -p 4222:4222 --rm nats:latest -DV 
echo "Wait 2 seconds to allow Nats to start..."
sleep 2


echo "Activate virtualenv"
. venv/bin/activate

echo "Starting consumer"
python consumer/q-app.py &

echo "Starting object identitfication"
python imageai/imageaiProcessor.py &

echo "Starting redaction"
python imageai/redaction.py &

echo "Starting producer"
# python producer/producer.py media/friends.mp4 &
python producer/producer.py WEBCAM &

echo "All running..."
