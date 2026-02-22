#!/bin/bash

cd "$(dirname "$0")"

while true; do
    .venv/Scripts/python.exe main.py
    echo "Bot crashed, restarting in 5 seconds..."
    sleep 5
done
