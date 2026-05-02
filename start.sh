#!/bin/bash

# Start the Aria2c daemon in the background with RPC enabled
aria2c --enable-rpc --rpc-listen-all=false --rpc-listen-port=6800 --daemon

# Start the Official Telegram C++ Local Bot API Server
# --local enables the file:// URI feature for uploading local files directly from disk
telegram-bot-api --local --api-id=${API_ID} --api-hash=${API_HASH} --http-port=8081 --dir=/app/tdlib &

# Wait for the local C++ server and Aria2c to initialize properly
echo "Waiting for services to start..."
sleep 3

# Run the Python Pyrogram Bot
python3 app.py