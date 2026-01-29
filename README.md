# Medium Article Topic Suggestion Agent

A production-ready AI agent built with **LangGraph** that helps you find the best topics for Medium articles based on your background, trending topics, and cutting-edge research.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **🌐 Modern Web UI**: Beautiful glassmorphism design with real-time progress updates
- **Model Agnostic**: Works with Ollama, Google Gemini, OpenAI, or Anthropic
- **Real-time Trend Analysis**: Searches DuckDuckGo for trending topics
- **Research-Backed**: Fetches latest papers from ArXiv
- **Smart Scoring**: Ranks topics across 5 dimensions (trend, uniqueness, engagement, author fit, research depth)
- **Interactive CLI**: Beautiful terminal interface with Rich
- **Production Ready**: Retry logic, structured logging, error handling

## 🏗️ Architecture

```
User Input → Input Validation → Web Search (DuckDuckGo)
                                     ↓
                              ArXiv Research
                                     ↓
                              Trend Analysis (LLM)
                                     ↓
                              Topic Generation (LLM)
                                     ↓
                              Scoring & Ranking (LLM)
                                     ↓
                              Ranked Topic Suggestions
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your preferred LLM provider:

**For Ollama (local, free):**
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

**For Google Gemini:**
```env
LLM_PROVIDER=google-genai
LLM_MODEL=gemini-2.0-flash
GOOGLE_API_KEY=your_api_key_here
```

### 3. Run the Agent

**Web UI (Recommended):**
```bash
python app.py
```
Then open [http://localhost:8000](http://localhost:8000) in your browser.

**CLI Mode:**
```bash
python main.py
```

## 🌐 Web UI

The web interface provides a modern, professional experience:

- **Glassmorphism Design**: Sleek dark mode with gradient accents
- **Real-time Progress**: WebSocket-powered live updates during generation
- **Score Visualizations**: Animated circular progress and detailed breakdowns
- **Smart Forms**: Tag-based keyword input with auto-save preferences
- **Responsive**: Works beautifully on desktop and mobile

### Features:
- 📊 Trend insights display (hot topics, emerging trends, content gaps)
- 🎯 Ranked topic cards with overall scores
- 📈 5-dimension score breakdown per topic
- 📋 One-click copy for topic details
- 💾 Auto-saves your preferences locally

## 📖 CLI Usage

### Interactive Mode

Simply run `python main.py` and follow the prompts:

1. Enter your professional background
2. Provide keywords/topics of interest (comma-separated)
3. Specify your target audience
4. Get ranked topic suggestions!

### Programmatic Usage

```python
from medium_topic_agent.agent import MediumTopicAgent

agent = MediumTopicAgent()

result = agent.run(
    background="Software engineer with 5 years of Python experience",
    keywords=["python", "fastapi", "microservices"],
    target_audience="intermediate developers",
    skip_clarification=True,  # Skip follow-up questions
)

if result["status"] == "success":
    for topic in result["topics"]:
        print(f"#{topic['rank']}: {topic['topic']['title']}")
        print(f"   Score: {topic['overall_score']:.1f}/100")
```

## 📊 Scoring Criteria

Each topic is scored on 5 dimensions (0-100):

| Score | Weight | Description |
|-------|--------|-------------|
| **Trend** | 20% | How trending/timely is the topic |
| **Uniqueness** | 20% | How differentiated from existing content |
| **Engagement** | 25% | Likelihood of claps, shares, comments |
| **Author Fit** | 20% | Match with your background |
| **Research Depth** | 15% | Backed by research/data |

**Overall Score** = Weighted average of all dimensions

## 🛠️ Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | LLM provider (ollama, google-genai, openai, anthropic) |
| `LLM_MODEL` | `llama3.2` | Model name for the selected provider |
| `MAX_TOPICS` | `10` | Maximum number of topics to generate |
| `MAX_SEARCH_RESULTS` | `10` | Max web search results per query |
| `MAX_ARXIV_RESULTS` | `5` | Max ArXiv papers to fetch |
| `LOG_LEVEL` | `INFO` | Logging level |

## 📁 Project Structure

```
├── app.py                    # FastAPI web server
├── main.py                   # CLI entry point
├── static/
│   ├── index.html            # Web UI HTML
│   ├── style.css             # Glassmorphism styles
│   └── script.js             # Frontend logic
└── medium_topic_agent/
    ├── __init__.py
    ├── agent.py              # Main LangGraph agent
    ├── config.py             # Configuration management
    ├── nodes/
    │   ├── input_collector.py
    │   ├── clarifier.py
    │   ├── web_searcher.py   # DuckDuckGo integration
    │   ├── arxiv_searcher.py # ArXiv integration
    │   ├── trend_analyzer.py
    │   ├── topic_generator.py
    │   └── scorer.py
    ├── schemas/
    │   ├── state.py          # Agent state definition
    │   └── models.py         # Pydantic models
    └── utils/
        ├── logger.py         # Structured logging
        └── retry.py          # Retry logic
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - feel free to use this in your projects!

