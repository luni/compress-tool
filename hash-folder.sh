#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi
cd "$1"
if [ -z "$2" ]; then
    HASH_FILENAME="$(basename "$(pwd)").sha256"
else
    HASH_FILENAME="$2.sha256"
fi

hashdeep -l -c sha256 -r . | awk -F, '!/^#/ {print $2 "  " $3}' | tee "$HASH_FILENAME"