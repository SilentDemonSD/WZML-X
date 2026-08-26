#!/bin/bash

ARIA2C=$1
SERVICE_CORES=${2:-}
CPU_LIMIT=${3:-20}
SABNZBDPLUS=$4

if [ -n "$SERVICE_CORES" ] && ! taskset -c "$SERVICE_CORES" true 2>/dev/null; then
    echo "setpkgs: cpus $SERVICE_CORES not usable here, pinning disabled" >&2
    SERVICE_CORES=""
fi

if [ -n "$SERVICE_CORES" ]; then
    ARIA2_CMD="taskset -c $SERVICE_CORES $ARIA2C"
    SAB_CMD="taskset -c $SERVICE_CORES cpulimit -l $CPU_LIMIT -- $SABNZBDPLUS"
else
    ARIA2_CMD="$ARIA2C"
    SAB_CMD="cpulimit -l $CPU_LIMIT -- $SABNZBDPLUS"
fi

tracker_list=$(curl -Ns https://cdn.jsdelivr.net/gh/ngosang/trackerslist@master/trackers_all.txt | awk '$0' | tr '\n\n' ',')
$ARIA2_CMD \
    --daemon=true \
    --rpc-listen-all=true \
    --enable-rpc=true \
    --rpc-max-request-size=1024M \
    --max-concurrent-downloads=1000 \
    --max-connection-per-server=16 \
    --split=16 \
    --min-split-size=32M \
    --optimize-concurrent-downloads=true \
    --continue=true \
    --auto-file-renaming=true \
    --allow-overwrite=true \
    --force-save=false \
    --content-disposition-default-utf8=true \
    --user-agent="Wget/1.12" \
    --http-accept-gzip=true \
    --max-tries=20 \
    --max-file-not-found=0 \
    --check-certificate=false \
    --bt-enable-lpd=true \
    --bt-detach-seed-only=true \
    --bt-remove-unselected-file=true \
    --bt-max-peers=0 \
    --bt-max-open-files=1000 \
    --bt-request-peer-speed-limit=1M \
    --seed-ratio=0 \
    --peer-id-prefix="-qB5220-" \
    --peer-agent="qBittorrent/5.2.2" \
    --follow-torrent=mem \
    --reuse-uri=true \
    --socket-recv-buffer-size=16M \
    --disable-ipv6=false \
    --connect-timeout=30 \
    --timeout=30 \
    --retry-wait=5 \
    --file-allocation=falloc \
    --disk-cache=64M \
    --check-integrity=true \
    --max-upload-limit=1K \
    --quiet=true \
    --summary-interval=0 \
    --save-session= \
    --save-session-interval=0 \
    --bt-tracker="[$tracker_list]"

if [ -n "$SABNZBDPLUS" ]; then
    $SAB_CMD -f configs/sabnzbd/SABnzbd.ini -s :::8070 -b 0 -d -c -l 0 --console
fi
