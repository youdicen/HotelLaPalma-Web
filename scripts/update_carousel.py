import os
import re
import requests
from datetime import datetime

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
if not APIFY_TOKEN:
    print("No APIFY_TOKEN environment variable found. Please set it. Skipping.")
    exit(0)

print("1. Triggering Apify Facebook Scraper...")
run_url = f"https://api.apify.com/v2/acts/apify~facebook-posts-scraper/runs?token={APIFY_TOKEN}"
act_input = {
    "startUrls": [{"url": "https://www.facebook.com/hotellapalma"}],
    "resultsLimit": 10
}

try:
    run_res = requests.post(run_url, json=act_input)
    run_res.raise_for_status()
    run_data = run_res.json()
    run_id = run_data['data']['id']
    dataset_id = run_data['data']['defaultDatasetId']
except Exception as e:
    print(f"Error starting Apify actor: {e}")
    exit(1)

print(f"Run ID: {run_id}. Waiting for it to finish...")
wait_url = f"https://api.apify.com/v2/actor-runs/{run_id}/waitForFinish?token={APIFY_TOKEN}"
requests.get(wait_url)

print("2. Fetching dataset items...")
dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}&format=json"
try:
    dataset_res = requests.get(dataset_url)
    dataset_res.raise_for_status()
    items = dataset_res.json()
except Exception as e:
    print(f"Error fetching Apify dataset: {e}")
    exit(1)

print(f"Found {len(items)} posts in dataset.")

html_slides = []
valid_posts = 0

for post in items:
    if valid_posts >= 5:
        break
    
    # We only want posts with an image/video thumbnail to look good in the carousel
    media = post.get('media', [])
    if not media:
        continue
        
    img_url = media[0].get('thumbnail') or media[0].get('url')
    if not img_url:
        continue
        
    text = post.get('text', '')
    if text and len(text) > 150:
        text = text[:147] + "..."
        
    raw_date = post.get('time', '')
    date_str = raw_date
    try:
        # Example facebook date string format: 2026-02-27T10:00:00+0000
        dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        date_str = dt.strftime("%d %b %Y")
    except:
        if len(raw_date) >= 10:
            date_str = raw_date[:10]
            
    post_url = post.get('url', '#')
    
    slide_html = f'''                <div class="carousel-slide">
                    <img src="{img_url}" alt="Post image">
                    <div class="carousel-slide-content">
                        <p class="post-date">{date_str}</p>
                        <p>{text}</p>
                        <a href="{post_url}" target="_blank" class="btn btn-outline" style="border-color: var(--color-accent-blue); color: var(--color-accent-blue); padding: 5px 15px; margin-top: 10px;">Ver en Facebook</a>
                    </div>
                </div>'''
    html_slides.append(slide_html)
    valid_posts += 1

if not html_slides:
    print("No valid posts found with media. Nothing to update.")
    exit(0)

slides_combined = "\n".join(html_slides)

print("3. Updating index.html...")
try:
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # We use a regex that matches the insertion point, or replaces everything inside the track
    pattern = re.compile(r'(<div class="carousel-track" id="carousel-track">)(.*?)(</div>\s*<button class="carousel-btn next-btn">)', re.DOTALL)
    
    new_html = pattern.sub(r'\1\n<!-- AUTOMATIC_CAROUSEL_INSERTION_POINT -->\n' + slides_combined + r'\n\3', html)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
        
    print("Success! index.html has been updated with the latest Facebook posts.")
except Exception as e:
    print(f"Error updating index.html: {e}")
    exit(1)
