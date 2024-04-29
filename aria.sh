#!/bin/bash

# Function to download the tracker list
download_tracker_list() {
  local url="$1"
  local output_file="$2"

  if ! curl -Ns "$url" > "$output_file"; then
    echo "Error: Failed to download tracker list"
    exit 1
  fi
}

# Download the tracker list and check if the curl command was successful
if ! download_tracker_list "https://ngosang.github.io/trackerslist/trackers_all_http.txt" "/tmp/trackers.txt"; then
  exit 1
fi

# Extract the tracker list from the downloaded file
tracker_list=$(cat "/tmp/trackers.txt" | awk '$0' | tr '\n\n' ',')

# Define the aria2 command with various options and arguments
aria2c --allow-overwrite=true \
       --auto-file-renaming=true \
       --bt-enable-lpd=true \
       --bt-detach-seed-only=true \
       --bt-remove-unselected-file=true \
       --bt-tracker="[$tracker_list]" \
       --bt-max-peers=0 \
       --enable-rpc=true \
       --rpc-max-request-size=1024M \
       --max-connection-per-server=10 \
       --max-concurrent-downloads=10 \
       --split=10 \
       --seed-ratio=0 \
       --check-integrity=true \
       --continue=true \
       --daemon=true \
       --disk-cache=40M \
       --force-save=true \
       --min-split-size=10M \
       --follow-torrent=mem \
       --check-certificate=false \
       --optimize-concurrent-downloads=true \
       --http-accept-gzip=true \
       --max-file-not-found=0 \
       --max-tries=20 \
       --peer-id-prefix=-qB4520- \
       --reuse-uri=true \
       --content-disposition-default-utf8=true \
       --user-agent=Wget/1.12 \
       --peer-agent=qBittorrent/4.5.2 \
       --quiet=true \
       --summary-interval=0 \
       --max-upload-limit=1K \
       -z \
       --log-level=error \
       --dir=/path/to/download/directory \
       --input-file=/path/to/torrent/file

# Check if the aria2 command was successful
if [ $? -ne 0 ]; then
  echo "Error: Failed to run aria2 command"
  exit 1
fi
