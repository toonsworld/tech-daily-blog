import os
import re
import json
import datetime
import feedparser
from google import genai

RSS_URL = "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en"
POSTS_DB = "posts.json"
SITE_TITLE = "TechPulse Daily"

def load_posts():
    if os.path.exists(POSTS_DB):
        with open(POSTS_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_posts(posts):
    with open(POSTS_DB, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

def get_trending_topic(existing_titles):
    feed = feedparser.parse(RSS_URL)
    for entry in feed.entries[:15]:
        title = entry.title.split(" - ")[0].strip()
        if title not in existing_titles:
            return title
    return None

def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[-\s]+', '-', text).strip('-')[:60]

def get_working_model(client):
    available = []
    for m in client.models.list():
        name = m.name.replace("models/", "")
        if "flash" in name.lower() and "image" not in name.lower() and "audio" not in name.lower():
            available.append(name)
    print("Available Flash models:", available)
    for m in available:
        if "3" in m or "2.5" in m or "2.0" in m:
            return m
    return available[0] if available else "gemini-2.0-flash"

def write_article(topic):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY missing!")

    client = genai.Client(api_key=api_key)
    model_name = get_working_model(client)
    print(f"Using model: {model_name}")

    prompt = f"""
    Write an engaging, original, SEO-optimized 700-word blog article in simple English about this trending tech news topic: "{topic}".
    
    Format the output strictly in clean HTML tags (only use <h2>, <h3>, <p>, <ul>, <li>, <strong> - do NOT include <html>, <head>, <body>, or markdown backticks).
    Include:
    - A catchy introduction
    - Key highlights / What happened
    - Why it matters to everyday users
    - A short FAQ section at the end
    """
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )
    content = response.text.strip()
    content = re.sub(r"^```html\s*|\s*```$", "", content)
    return content

def build_html_pages(posts):
    os.makedirs("posts", exist_ok=True)
    
    base_style = """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.7; color: #222; max-width: 800px; margin: 0 auto; padding: 20px; background: #f9fafb; }
        header { background: #111827; color: #fff; padding: 20px; border-radius: 10px; margin-bottom: 30px; text-align: center; }
        header a { color: #fff; text-decoration: none; font-size: 26px; font-weight: bold; }
        .card { background: #fff; padding: 22px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
        .card h2 { margin-top: 0; font-size: 22px; }
        .card h2 a { color: #1d4ed8; text-decoration: none; }
        .meta { color: #6b7280; font-size: 14px; margin-bottom: 12px; }
        article { background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        footer { text-align: center; margin-top: 40px; color: #6b7280; font-size: 14px; }
    </style>
    """

    for post in posts:
        post_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{post['title']} - {SITE_TITLE}</title>
    <meta name="description" content="{post['title']} - Latest tech update and analysis.">
    {base_style}
</head>
<body>
    <header><a href="../index.html">{SITE_TITLE}</a></header>
    <article>
        <h1>{post['title']}</h1>
        <div class="meta">Published on {post['date']} • Tech & AI</div>
        {post['content']}
    </article>
    <footer>© {datetime.datetime.now().year} {SITE_TITLE} | <a href="../index.html">Home</a></footer>
</body>
</html>"""
        with open(f"posts/{post['slug']}.html", "w", encoding="utf-8") as f:
            f.write(post_html)

    cards_html = ""
    for post in reversed(posts[-20:]):
        cards_html += f"""
        <div class="card">
            <div class="meta">{post['date']}</div>
            <h2><a href="posts/{post['slug']}.html">{post['title']}</a></h2>
            <p>Read our full breakdown and analysis on {post['title']}...</p>
        </div>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{SITE_TITLE} - Latest Tech & AI News</title>
    {base_style}
</head>
<body>
    <header><a href="index.html">{SITE_TITLE}</a><p style="margin:5px 0 0;font-size:14px;color:#9ca3af;">Daily Tech, AI & Digital Updates</p></header>
    {cards_html}
    <footer>© {datetime.datetime.now().year} {SITE_TITLE}</footer>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

if __name__ == "__main__":
    posts = load_posts()
    existing_titles = {p["title"] for p in posts}
    topic = get_trending_topic(existing_titles)

    if not topic:
        print("Koi naya topic nahi mila.")
    else:
        print(f"Writing article on: {topic}")
        article_html = write_article(topic)
        new_post = {
            "title": topic,
            "slug": slugify(topic),
            "date": datetime.date.today().strftime("%B %d, %Y"),
            "content": article_html
        }
        posts.append(new_post)
        save_posts(posts)
        build_html_pages(posts)
        print("Website updated successfully!")
    
