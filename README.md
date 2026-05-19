# 🗂️ Brochure Generator

Generate a polished company brochure from just a **name** and **URL** — powered by a local Ollama LLM (qwen2.5), Flask, and a clean browser UI.

---

## 🏗️ Architecture

```
Browser (index.html)
        │
        │  POST /generate { company_name, url }
        ▼
┌─────────────────────────────────────────┐
│           Flask Server (app.py)         │
│                                         │
│  1. fetch_website_links(url)            │  ← scraper.py gets all links
│          │                              │
│  2. select_relevant_links(url)          │  ← qwen2.5 picks best 2–3 links
│          │                              │     (About, Careers, Company)
│  3. fetch_website_contents(url)         │  ← scraper.py fetches each page
│          │                              │
│  4. get_brochure_user_prompt()          │  ← assembles scraped content
│          │                              │     into a single prompt
│  5. stream brochure tokens              │  ← qwen2.5 generates markdown
│                                         │     streamed token by token
└─────────────────────────────────────────┘
        │
        │  SSE stream  { status / token / done }
        ▼
Browser renders markdown live as it arrives
```

---

## 🔄 How It Works Step by Step

| Step | What Happens |
|------|-------------|
| 1 | User enters company name + URL in the browser |
| 2 | Flask scrapes all links from the homepage via `scraper.py` |
| 3 | qwen2.5 reads the link list and picks the most relevant pages (About, Careers etc.) |
| 4 | Flask fetches the content of each relevant page |
| 5 | All page contents are assembled into a single prompt (truncated to 5,000 chars) |
| 6 | qwen2.5 streams a markdown brochure token by token back to the browser |
| 7 | Browser renders the brochure live as tokens arrive |

---

## 📁 Project Structure

```
brochure_generator/
├── app.py           # Flask backend — scraping + LLM + SSE streaming
├── index.html       # Browser UI — form, live markdown rendering
├── scraper.py       # fetch_website_links() and fetch_website_contents()
├── brochure.ipynb   # Original Jupyter notebook prototype
├── .env             # Environment variables (not committed)
├── .env.example     # Template for .env
└── README.md
```

---

## ⚙️ Setup

**1. Install dependencies**
```bash
pip install flask flask-cors openai python-dotenv requests beautifulsoup4
```

**2. Pull the model**
```bash
ollama pull qwen2.5
```

**3. Start Ollama**
```bash
ollama serve
```

**4. Run the app**
```bash
cd brochure_generator
python app.py
```

**5. Open in browser**
```
http://localhost:5000
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | qwen2.5 via Ollama (runs fully locally) |
| Backend | Python + Flask |
| Scraping | BeautifulSoup + Requests |
| Streaming | Server-Sent Events (SSE) |
| Frontend | Vanilla HTML/CSS/JS + marked.js |

---

## 💡 Key Design Decisions

- **Local LLM** — qwen2.5 runs on your machine via Ollama, no API keys or cloud costs
- **Two LLM calls** — first call picks relevant links (fast, small output), second call writes the brochure (streamed)
- **SSE streaming** — brochure text appears word by word in the browser instead of waiting for the full response
- **5,000 char limit** — prompt is truncated to keep inference fast on local hardware
