# Brochure Generator

Generate company brochures from a URL using a local Ollama model.

## Setup
```bash
pip install flask flask-cors openai python-dotenv requests beautifulsoup4
ollama pull qwen2.5
```

## Run
```bash
python app.py
```
Open http://localhost:5000

## Requirements
- Ollama running locally (`ollama serve`)
- qwen2.5 model pulled
