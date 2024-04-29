#!/bin/bash

# Check if the update.py script exists before running it
if [ -f update.py ]; then
  echo "Running update.py..."
  python3 update.py

  # Check if the bot module can be imported before running it
  if python3 -c "import bot"; then
    echo "Running bot..."
    python3 -m bot
  else
    echo "Error: bot module not found or import failed."
  fi
else
  echo "Error: update.py not found or not a file."
fi
