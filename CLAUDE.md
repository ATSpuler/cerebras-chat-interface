# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project that demonstrates integration with the Cerebras AI API using their cloud SDK. The project consists of a Jupyter notebook that shows how to make API calls to Cerebras AI models, specifically the Qwen-3-Coder-480B model.

## Setup and Dependencies

The project requires two main Python packages:
- `python-dotenv` - for environment variable management
- `cerebras_cloud_sdk` - Cerebras AI cloud SDK

Install dependencies using:
```bash
uv pip install python-dotenv
uv pip install cerebras_cloud_sdk
```

## Environment Configuration

The project expects a `.env` file with:
- `CEREBRAS_API_KEY` - Your Cerebras API key for authentication

## Code Architecture

### Main Components

- **CEREBRAS_WORKING_API_CALLS.ipynb**: The primary notebook containing:
  - Environment setup and API key loading
  - Cerebras client initialization
  - Example API calls with streaming responses
  - Demonstrates both system message handling and model queries

### API Usage Pattern

The notebook shows the standard pattern for Cerebras API calls:
1. Load environment variables using `dotenv`
2. Initialize Cerebras client with API key
3. Create chat completions using `client.chat.completions.create()`
4. Handle streaming responses with proper iteration

### Model Configuration

Default model parameters used:
- Model: `qwen-3-coder-480b`
- Stream: `True` (for real-time responses)
- Max tokens: `40000`
- Temperature: `0.7`
- Top-p: `0.8`

## Running the Code

### Jupyter Notebook
Execute the Jupyter notebook cells in sequence:
1. Install dependencies (cells 0)
2. Import modules (cell 1)
3. Load environment (cell 2)
4. Set up API key (cell 3)
5. Initialize client (cell 4)
6. Run API calls (cells 5-6)

### Chat Interface
A Gradio-based web chat interface is available:

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your Cerebras API key
3. Run: `python chat_app.py`
4. Open browser to `http://localhost:7860`

**Chat Interface Features:**
- Real-time streaming responses
- Conversation history
- Pre-defined example prompts
- Error handling and recovery

**Files:**
- `chat_app.py` - Main Gradio application
- `cerebras_client.py` - Cerebras API wrapper with streaming support
- `requirements.txt` - All dependencies
- `.env.example` - Environment template