#!/bin/bash

# This script checks if the update.py script exists and runs it if it does.
# The 'if' statement checks if the file update.py exists in the current directory.
if [ -f update.py ]; then
  echo "Running update.py..."
  
  # The 'python3' command runs the update.py script.
  python3 update.py

  # After running update.py, the script checks if the 'bot' module can be imported.
  # The 'if' statement checks if the 'bot' module can be imported without errors.
  if python3 -c "import bot"; then
    echo "Running bot..."
    
    # The 'python3' command runs the 'bot' module as a module (-m flag).
    python3 -m bot
  else
    echo "Error: bot module not found or import failed."
  fi
else
  echo "Error: update.py not found or not a file."
fi

