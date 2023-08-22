#!/bin/bash

# Endpoint URL
ENDPOINT="https://nsfw-server-gvx56wdn4a-an.a.run.app"  # replace 'your_flask_app_address' with your Flask app's actual address

# Folder containing the files
FOLDER_PATH="./test-images/pack"  # replace this with your actual folder path

# Construct the curl command with all the files
CURL_CMD="curl -X POST"
for file in "$FOLDER_PATH"/*; do
    if [[ -f "$file" ]]; then
        CURL_CMD="$CURL_CMD -F files[]=@\"$file\""
    fi
done

# Add the endpoint to the curl command and execute it
CURL_CMD="$CURL_CMD $ENDPOINT"
eval "$CURL_CMD"
echo ""  # Newline for readability
