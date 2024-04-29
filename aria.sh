#!/bin/bash

# Function to download a file
# This function accepts three arguments:
# $1: The URL of the file to download
# $2: The output file path
# $3: The optional expected file size, used to check if the download was successful
# It downloads the file using curl and saves it to the specified output file.
# If the download is not successful or the file size does not match the expected size,
# the function returns 1.
download_file() {
  local url="$1"
  local output_file="$2"
  local expected_size="$3"

  if ! curl -Ns "$url" -o "$output_file"; then
    echo "Error: Failed to download $url"
    return 1
  fi

  if [ -n "$expected_size" ] && [ "$(stat -c%s "$output_file")" -ne "$expected_size" ]; then
    echo "Error: Downloaded file size does not match expected size"
    return 1
  fi

  echo "Download successful"
}

# Download the tracker list from the given URL and save it to /tmp/trackers.txt
TRACKERS_URL="https://ngosang.github.io/trackerslist/trackers_all_http.txt"
TRACKERS_FILE="/tmp/trackers.txt"
if ! download_file "$TRACKERS_URL" "$TRACKERS_FILE" ""; then
  echo "Error: Failed to download tracker list"
  exit 1
fi

