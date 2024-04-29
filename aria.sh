#!/bin/bash

# Get the tracker list from the specified URL and check if the curl command was successful
if ! tracker_list=$(curl -Ns https://ngosang.github.io/trackerslist/trackers_all_http.txt | awk '$0' | tr '\n\n' ','); then
  # If the command was not successful, print an error message and exit the script with a non-zero status code
  echo "Error: Failed to download tracker list"
  exit 1
fi

# Define the aria2 command with various options and arguments
aria2c --allow-overwrite=true \ # Allow overwriting existing files
       --auto-file-renaming=true \ # Automatically rename downloaded files
       --bt-enable-lpd=true \ # Enable Local Peer Discovery
       --bt-detach-seed-only=true \ # Detach seeding torrents
       --bt-remove-unselected-file=true \ # Remove unselected files from torrent
       --bt-tracker="[$tracker_list]" \ # Specify the tracker list
       --bt-max-peers=0 \ # Set maximum number of peers to 0 (unlimited)
       --enable-rpc=true \ # Enable RPC server
       --rpc-max-request-size=1024M \ # Set maximum request size to 1024 MB
       --max-connection-per-server=10 \ # Set maximum connections per server to 10
       --max-concurrent-downloads=10 \ # Set maximum concurrent downloads to 10
       --split=10 \ # Set number of pieces to download simultaneously to 10
       --seed-ratio=0 \ # Set seed ratio to 0 (do not seed)
       --check-integrity=true \ # Verify file integrity after download
       --continue=true \ # Resume downloading stopped torrents
       --daemon=true \ # Run aria2 in daemon mode
       --disk-cache=40M \ # Set disk cache to 40 MB
       --force-save=true \ # Force saving the file even if the metadata is incomplete
       --min-split-size=10M \ # Set minimum split size to 10 MB
       --follow-torrent=mem \ # Follow torrent metadata in memory
       --check-certificate=false \ # Do not check SSL certificates
       --optimize-concurrent-downloads=true \ # Optimize concurrent downloads
       --http-accept-gzip=true \ # Accept gzip-encoded HTTP responses
       --max-file-not-found=0 \ # Do not stop downloading if a file is not found
       --max-tries=20 \ # Set maximum number of retries to 20
       --peer-id-prefix=-qB4520- \ # Set peer ID prefix
       --reuse-uri=true \ # Reuse URI when downloading multiple files
       --content-disposition-default-utf8=true \ # Set Content-Disposition header to UTF-8
       --user-agent=Wget/1.12 \ # Set user agent to Wget/1.12
       --peer-agent=qBittorrent/4.5.2 \ # Set peer user agent to qBittorrent/4.5.2
       --quiet=true \ # Run in quiet mode
       --summary-interval=0 \ # Set summary interval to 0 (disable summary)
       --max-upload-limit=1K \ # Set maximum upload limit to 1 KB
       -z \ # Download metadata only
       --log-level=error \ # Set log level to error
       --dir=/path/to/download/directory \ # Set download directory
       --input-file=/path/to/torrent/file \ # Set input torrent file
