#!/bin/bash

# Create or attach to tmux session named 'chat-app'
tmux new-session -d -s chat-app

# Send commands to the session
tmux send-keys -t chat-app 'source .venv/bin/activate' Enter
tmux send-keys -t chat-app 'python chat_app.py' Enter

# Attach to the session
# tmux attach-session -t chat-app
