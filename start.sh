#!/usr/bin/env bash

# Check if python3 is installed and is a regular file
if ! [ -x "$(command -v python3)" ] || ! [ -r "$(command -v python3)" ]; then
    # If python3 is not installed or not readable, print an error message and exit with a status of 1
    echo "Error: python3 not installed or not readable."
    exit 1
fi

# Get the absolute path to this script
SCRIPT_DIR="$(readlink -f "${BASH_SOURCE[0]}")"

# Absolute path to update.py
UPDATE_PY="$SCRIPT_DIR/update.py"

# Check if update.py exists, is a regular file, readable, and executable
if [ -f "$UPDATE_PY" ] && [ -r "$UPDATE_PY" ] && [ -x "$UPDATE_PY" ]; then
  # If update.py exists and is readable and executable, print a message and continue to the next step
  echo "Running update.py..."

  # Create a temporary directory to store the logs
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' INT TERM EXIT

  # Run update.py with error handling, redirecting output to a log file
  if ! python3 "$UPDATE_PY" > "$TMP_DIR/update.log" 2>&1; then
    # If update.py fails to run, print an error message, display the contents of the log file, and exit with a status of 1
    echo "Error: update.py failed to run."
    cat "$TMP_DIR/update.log"
    exit 1
  fi

  # Absolute path to the bot module
  BOT_MODULE="$SCRIPT_DIR/bot.py"

  # Check if bot.py exists, is a regular file, and readable
  if [ -f "$BOT_MODULE" ] && [ -r "$BOT_MODULE" ]; then
    # If bot.py exists and is readable, print a message and continue to the next step
    echo "Running bot..."

    # Create a temporary directory to store the logs
    TMP_DIR_BOT="$(mktemp -d)"
    trap 'rm -rf "$TMP_DIR_BOT"' INT TERM EXIT

    # Run the bot module as a module with error handling, redirecting output to a log file
    if ! python3 -m bot > "$TMP_DIR_BOT/bot.log" 2>&1; then
      # If the bot module fails to run, print an error message, display the contents of the log file, and exit with a status of 1
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
    # If bot.py is not found or not readable, print an error message and exit with a status of 1
    echo "Error: bot.py not found or not readable."
    exit 1
  fi
else
  # If update.py is not found, not a file, not readable, or not executable, print an error message and exit with a status of 1
  echo "Error: update.py not found, not a file, not readable, or not executable."
  exit 1
fi
