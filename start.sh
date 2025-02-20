#!/bin/bash

# Start Flask in the background
python3 app.py & 

# Run bot update and start bot
python3 update.py && python3 -m bot
