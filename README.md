# Cerebras AI Chat Interface

A modern web-based chat interface for the Cerebras AI API using Gradio, featuring persistent conversation history with SQLite storage.

## ✨ Features

- **Real-time streaming responses** - See AI responses as they're generated
- **Persistent chat history** - All conversations automatically saved to SQLite database  
- **Clean, modern UI** - Built with Gradio's ChatInterface
- **Conversation management** - Automatic conversation creation and titling
- **Example prompts** - Quick start with pre-defined examples
- **Error handling** - Graceful failure recovery

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Cerebras AI API key ([get one here](https://cerebras.ai/))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd cerebras-chat-interface
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your CEREBRAS_API_KEY
   ```

4. **Run the chat interface**
   ```bash
   python chat_app.py
   ```

5. **Open in browser**
   - Navigate to `http://localhost:7860`
   - Start chatting!

## 🏗️ Architecture

### Core Components

- **`chat_app.py`** - Main Gradio application with streaming chat interface
- **`cerebras_client.py`** - Cerebras API wrapper with streaming support
- **`chat_history.py`** - SQLite-based conversation persistence using APSW
- **`CEREBRAS_WORKING_API_CALLS.ipynb`** - Original API exploration notebook

### Database Schema

The chat history uses SQLite with two main tables:
- `conversations` - Conversation metadata (ID, title, timestamps)
- `messages` - Individual messages with role (user/assistant) and content

### API Integration

- **Model**: Qwen-3-Coder-480B (Cerebras Cloud)
- **Streaming**: Real-time response chunks
- **Parameters**: Temperature 0.7, Top-p 0.8, Max tokens 40K

## 📁 Project Structure

```
cerebras-chat-interface/
├── chat_app.py              # Main Gradio application
├── cerebras_client.py       # API client wrapper
├── chat_history.py          # SQLite conversation storage
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── .gitignore              # Git ignore patterns
├── LICENSE                 # MIT License
├── README.md               # This file
├── CLAUDE.md               # Development guidance
└── CEREBRAS_WORKING_API_CALLS.ipynb  # Original exploration
```

## 🔧 Configuration

### Environment Variables

- `CEREBRAS_API_KEY` - Your Cerebras AI API key (required)

### Model Parameters

Default configuration in `cerebras_client.py`:
- Model: `qwen-3-coder-480b`
- Temperature: `0.7`
- Top-p: `0.8`  
- Max completion tokens: `40000`
- Streaming: `True`

## 🛠️ Development

### Running from Notebook

The original Jupyter notebook (`CEREBRAS_WORKING_API_CALLS.ipynb`) demonstrates basic API usage:

1. Install dependencies: `uv pip install python-dotenv cerebras_cloud_sdk`
2. Run cells sequentially to test API connectivity

### Extending the Interface

The modular architecture makes it easy to add features:
- **New models**: Modify `cerebras_client.py`
- **UI enhancements**: Extend `chat_app.py` 
- **Storage options**: Replace `chat_history.py`

## 📊 Chat History Features

- **Automatic saving** - Every conversation and message stored
- **Conversation titling** - Auto-generated from first message
- **APSW SQLite** - High-performance SQLite interface
- **Conversation search** - Search by title or content
- **Statistics** - Track usage and conversation counts

## 🚀 Deployment

### Local Development
```bash
python chat_app.py
# Access at http://localhost:7860
```

### Production Deployment
- Set `share=False` in `chat_app.py` for local-only access
- Use reverse proxy (nginx) for external access
- Consider Docker containerization for easy deployment

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

Built by **Albin**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🐛 Issues & Support

Please report issues on the [GitHub Issues](../../issues) page.

---

*Powered by Cerebras AI • Built with Gradio*