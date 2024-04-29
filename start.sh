#!/usr/bin/env bash

# Check if python3 is installed
if ! type -P python3 &> /dev/null; then
    echo "Error: python3 not installed."
    exit 1
fi

# Absolute path to this script
SCRIPT_DIR="$(readlink -f "${BASH_SOURCE[0]}")"

# Absolute path to update.py
UPDATE_PY="$SCRIPT_DIR/update.py"

# Create a temporary directory to store the logs
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' INT TERM EXIT

# Check if update.py exists and is a file
if [ -f "$UPDATE_PY" ]; then
  echo "Running update.py..."
  
  # Run update.py with error handling
  if ! python3 "$UPDATE_PY" > "$TMP_DIR/update.log" 2>&1; then
    echo "Error: update.py failed to run."
    cat "$TMP_DIR/update.log"
    exit 1
  fi

  # Absolute path to the bot module
  BOT_MODULE="$SCRIPT_DIR/bot"

  # Check if the bot module can be imported without errors
  if python3 -c "import bot" > /dev/null 2>&1; then
    echo "Running bot..."
    
    # Run the bot module as a module with error handling
    if ! python3 -m bot > "$TMP_DIR/bot.log" 2>&1; then
      echo "Error: bot module failed to run."
      cat "$TMP_DIR/bot.log"
      exit 1
    fi
  else
    echo "Error: bot module not found or import failed."
  fi
else
  echo "Error: update.py not found or not a file."
fi

# Display the logs on the terminal
echo "Update logs:"
cat "$TMP_DIR/update.log"
echo "Bot logs:"
cat "$TMP_DIR/bot.log"
