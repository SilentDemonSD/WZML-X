#!/bin/bash

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not installed."
    exit 1
fi

# Absolute path to this script
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Absolute path to update.py
UPDATE_PY="$SCRIPT_DIR/update.py"

# Check if update.py exists and is a file
if [ -f "$UPDATE_PY" ]; then
  echo "Running update.py..."
  
  # Run update.py with error handling
  if ! python3 "$UPDATE_PY" &> /dev/null; then
    echo "Error: update.py failed to run."
    exit 1
  fi

  # Absolute path to the bot module
  BOT_MODULE="$SCRIPT_DIR/bot"

  # Check if the bot module can be imported without errors
  if python3 -c "import bot" &> /dev/null; then
    echo "Running bot..."
    
    # Run the bot module as a module with error handling
    if ! python3 -m bot &> /dev/null; then
      echo "Error: bot module failed to run."
      exit 1
    fi
  else
    echo "Error: bot module not found or import failed."
  fi
else
  echo "Error: update.py not found or not a file."
fi
