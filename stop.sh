#!/bin/bash -x

echo "Kill image-pipeline processes..."

pkill -f q-app.py
pkill -f producer.py
pkill -f imageaiProcessor.py
pkill -f redaction.py

docker kill nats

echo "All killed"
