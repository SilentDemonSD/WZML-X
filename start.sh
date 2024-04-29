#!/usr/bin/env bash

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not installed."
    exit 1
fi

# Absolute path to this script
SCRIPT_DIR="$(readlink -f "${BASH_SOURCE[0]}")"

# Absolute path to update.py
UPDATE_PY="$SCRIPT_DIR/update.py"

# Check if update.py exists and is a regular file
if [ -f "$UPDATE_PY" ] && [ -r "$UPDATE_PY" ] && [ -x "$UPDATE_PY" ]; then
  echo "Running update.py..."

  # Create a temporary directory to store the logs
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' INT TERM EXIT

  # Run update.py with error handling
  if ! python3 "$UPDATE_PY" > "$TMP_DIR/update.log" 2>&1; then
    echo "Error: update.py failed to run."
    cat "$TMP_DIR/update.log"
    exit 1
  fi

  # Absolute path to the bot module
  BOT_MODULE="$SCRIPT_DIR/bot.py"

  # Check if the bot module can be imported without errors
  if python3 -c "import bot" &> /dev/null; then
    echo "Running bot..."

    # Create a temporary directory to store the logs
    TMP_DIR_BOT="$(mktemp -d)"
    trap 'rm -rf "$TMP_DIR_BOT"' INT TERM EXIT

    # Run the bot module as a module with error handling
    if ! python3 -m bot > "$TMP_DIR_BOT/bot.log" 2>&1; then
      echo "Error: bot module failed to run."
      cat "$TMP_DIR_BOT/bot.log"
      exit 1
    fi

    # Display the logs on the terminal
    echo "Update logs:"
    cat "$TMP_DIR/update.log"
    echo "Bot logs:"
    cat "$TMP_DIR_BOT/bot.log"

  else
    echo "Error: bot module not found or import failed."
  fi
else
  echo "Error: update.py not found, not a file, not readable, or not executable."
fi
