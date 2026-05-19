import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from scraper import fetch_website_links, fetch_website_contents
from openai import OpenAI

load_dotenv()

app = Flask(__name__, static_folder=".")
CORS(app)

openai = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama'
)

MAX_LINKS    = 2      # only fetch 2 sub-pages max
PAGE_TIMEOUT = 8      # seconds per HTTP fetch
PROMPT_LIMIT = 4_000  # chars sent to model

# ── Prompts ───────────────────────────────────────────────────────────────────

links_system_prompt = """
You are provided with a list of links found on a webpage.
Decide which links are most relevant for a company brochure (About, Company, Careers).
Pick at most 2 links.
Respond only in JSON like:
{"links": [{"type": "about page", "url": "https://example.com/about"}]}
"""

brochure_system_prompt = """
You are an assistant that analyzes the contents of several relevant pages from a company website
and creates a short brochure about the company for prospective customers, investors and recruits.
Respond in markdown without code blocks.
Include details of company culture, customers and careers/jobs if you have the information.
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_fetch(url):
    """Fetch page content; return empty string on failure/timeout."""
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(fetch_website_contents, url).result(timeout=PAGE_TIMEOUT)
    except Exception:
        return ""


def build_prompt_with_updates(company_name, url):
    """
    Generator that yields ("status", msg) during work,
    then ("prompt", text) as the final item.
    """
    yield ("status", "Fetching homepage…")

    # Fetch homepage and raw link list concurrently
    with ThreadPoolExecutor(max_workers=2) as ex:
        homepage_fut = ex.submit(safe_fetch, url)
        links_fut    = ex.submit(fetch_website_links, url)
        homepage = homepage_fut.result()
        links    = links_fut.result()

    yield ("status", "Asking model to pick relevant links…")

    links_prompt = (
        f"Links on {url}:\n" + "\n".join(links)
    )
    resp = openai.chat.completions.create(
        model="qwen2.5:latest",
        messages=[
            {"role": "system", "content": links_system_prompt},
            {"role": "user",   "content": links_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=200,   # ← tiny output = fast
    )
    chosen = json.loads(resp.choices[0].message.content).get("links", [])[:MAX_LINKS]

    # Fetch sub-pages concurrently
    sub_pages = {}
    if chosen:
        yield ("status", f"Fetching {len(chosen)} sub-page(s) in parallel…")
        with ThreadPoolExecutor(max_workers=MAX_LINKS) as ex:
            futures = {ex.submit(safe_fetch, lnk["url"]): lnk for lnk in chosen}
            for fut in as_completed(futures):
                lnk = futures[fut]
                sub_pages[lnk["type"]] = fut.result()

    # Assemble final prompt
    yield ("status", "Building prompt…")
    prompt = (
        f"Company: {company_name}\n\n"
        f"## Landing page\n\n{homepage}\n\n"
    )
    for page_type, content in sub_pages.items():
        prompt += f"\n\n## {page_type}\n\n{content}"

    yield ("prompt", prompt[:PROMPT_LIMIT])


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data         = request.get_json()
    company_name = data.get("company_name", "").strip()
    url          = data.get("url", "").strip()

    if not company_name or not url:
        return jsonify({"error": "Both company_name and url are required."}), 400

    def event_stream():
        try:
            user_prompt = None

            # Phase 1 — scrape + build prompt with live status updates
            for kind, value in build_prompt_with_updates(company_name, url):
                if kind == "status":
                    yield f"data: {json.dumps({'status': value})}\n\n"
                elif kind == "prompt":
                    user_prompt = value

            # Phase 2 — stream brochure tokens from Ollama
            yield f"data: {json.dumps({'status': 'Generating brochure…'})}\n\n"

            stream = openai.chat.completions.create(
                model="qwen2.5:latest",
                messages=[
                    {"role": "system", "content": brochure_system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                stream=True,
            )

            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)