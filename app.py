import json
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from scraper import fetch_website_links, fetch_website_contents
from openai import OpenAI

load_dotenv()

app = Flask(__name__, static_folder=".")
CORS(app)

# Connect to local Ollama
openai = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama'
)

# ── Prompts ───────────────────────────────────────────────────────────────────

links_system_prompt = """
You are provided with a list of links found on a webpage.
You are able to decide which of the links would be most relevant to include in a brochure about the company,
such as links to an About page, or a Company page, or Careers/Jobs pages.
You should respond in JSON as in this example:

{
    "links": [
        {"type": "about page", "url": "https://openai.com/about"},
        {"type": "careers page", "url": "https://openai.com/careers"}
    ]
}
"""

brochure_system_prompt = """
You are an assistant that analyzes the contents of several relevant pages from a company website
and creates a short brochure about the company for prospective customers, investors and recruits.
Respond in markdown without code blocks.
Include details of company culture, customers and careers/jobs if you have the information.
"""

# ── Your original notebook functions (unchanged) ──────────────────────────────

def get_links_user_prompt(url):
    user_prompt = f"Here is the list of links on the website {url} - \n"
    user_prompt += "Please decide which of these are relevant web links for a brochure about the company, "
    user_prompt += "respond with the full https URL in JSON format. "
    user_prompt += "Do not include Terms of Service, Privacy, email links.\n\nLinks (some might be relative links):\n\n"
    links = fetch_website_links(url)
    user_prompt += "\n".join(links)
    return user_prompt


def select_relevant_links(url):
    response = openai.chat.completions.create(
        model="qwen2.5:latest",
        messages=[
            {"role": "system", "content": links_system_prompt},
            {"role": "user", "content": get_links_user_prompt(url)}
        ],
        response_format={"type": "json_object"}
    )
    result = response.choices[0].message.content
    links = json.loads(result)
    return links


def fetch_page_and_all_relevant_links(url):
    contents = fetch_website_contents(url)
    relevant_links = select_relevant_links(url)
    result = f"## Landing page content for {url} \n\n {contents} \n\n"
    for link in relevant_links['links']:
        result += f"\n\n## Content for {link['type']}"
        result += fetch_website_contents(link["url"])
    return result


def get_brochure_user_prompt(company_name, url):
    user_prompt = f"You are looking at a company called: {company_name}\n"
    user_prompt += "Here are the contents of its landing page and other relevant pages; "
    user_prompt += "use this information to build a short brochure of the company in markdown without code blocks.\n\n"
    user_prompt += fetch_page_and_all_relevant_links(url)
    user_prompt = user_prompt[:5_000]  # Truncate if more than 5,000 characters
    return user_prompt


# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    company_name = data.get("company_name", "").strip()
    url = data.get("url", "").strip()

    if not company_name or not url:
        return jsonify({"error": "Both company_name and url are required."}), 400

    def event_stream():
        try:
            # Step 1 - scraping status
            yield f"data: {json.dumps({'status': 'Fetching website links...'})}\n\n"

            # Step 2 - ask model to pick links (your original select_relevant_links)
            yield f"data: {json.dumps({'status': 'Selecting relevant links...'})}\n\n"

            # Step 3 - build the full prompt (your original get_brochure_user_prompt)
            yield f"data: {json.dumps({'status': 'Fetching page contents...'})}\n\n"
            user_prompt = get_brochure_user_prompt(company_name, url)

            # Step 4 - stream brochure from Ollama (your original stream_brochure logic)
            yield f"data: {json.dumps({'status': 'Generating brochure...'})}\n\n"

            stream = openai.chat.completions.create(
                model="qwen2.5:latest",
                messages=[
                    {"role": "system", "content": brochure_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True
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