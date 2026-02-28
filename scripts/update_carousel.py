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

import time

print(f"Run ID: {run_id}. Waiting for it to finish...")
status = "RUNNING"
while status in ["READY", "RUNNING"]:
    time.sleep(5)
    run_status_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}")
    if run_status_res.status_code == 200:
        status = run_status_res.json()['data']['status']
        print(f"Current status: {status}")
    else:
        print("Error checking status")
        break

if status != "SUCCEEDED":
    print(f"Run did not succeed. Status: {status}")
    exit(1)

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
blog_posts_html = []
valid_posts = 0

for post in items:
    # We only want posts with an image/video thumbnail to look good in the carousel and blog

    media = post.get('media', [])
    img_url = '2022-07-13.webp'
    if media:
        img_url = media[0].get('thumbnail') or media[0].get('url') or '2022-07-13.webp'

        
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
    
    # --- For Blog (All valid posts) ---
    blog_html = f'''            <article class="blog-post">
                <img src="{img_url}" alt="Imagen del post" class="blog-image" onerror="this.onerror=null; this.src='2022-07-13.webp';">
                <div class="blog-content">
                    <div class="blog-date">{date_str}</div>
                    <div class="blog-text">{text}</div>
                    <div class="blog-btn-container">
                        <a href="{post_url}" target="_blank" class="btn btn-outline" style="color: var(--color-accent-blue); border-color: var(--color-accent-blue);">
                            Ver en Facebook
                        </a>
                    </div>
                </div>
            </article>'''
    blog_posts_html.append(blog_html)
    
    # --- For Carousel (Only first 5 valid posts) ---
    if valid_posts < 5:
        short_text = text
        if short_text and len(short_text) > 150:
            short_text = short_text[:147] + "..."
            
        slide_html = f'''            <div class="hero-slide">
                <img class="hero-background" src="{img_url}" onerror="this.onerror=null; this.src='2022-07-13.webp';" style="object-fit: cover;">
                <div class="hero-overlay"></div>
                <div class="hero-content">
                    <h2 class="hero-title" style="font-size: clamp(2rem, 4vw, 3.5rem); margin-bottom: 20px;">{date_str}</h2>
                    <p class="hero-subtitle" style="max-width: 600px; margin: 0 auto 30px auto;">
                        {short_text}
                    </p>
                    <a href="{post_url}" target="_blank" class="btn btn-primary"
                        style="font-size: 1.1rem; padding: 12px 30px; border: 2px solid var(--color-accent-blue); background-color: var(--color-accent-blue); color: var(--color-text-light);">
                        Ver Novedad en Facebook
                    </a>
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

    # We use a regex down from the insertion point to the end of the track to preserve the static slide
    pattern = re.compile(r'(<!-- AUTOMATIC_HERO_CAROUSEL_INSERTION_POINT -->)(.*?)(</div>\s*<button class="hero-carousel-btn hero-next-btn">)', re.DOTALL)
    
    new_html = pattern.sub(r'\1\n' + slides_combined + r'\n\3', html)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
        
    print("Success! index.html has been updated with the latest Facebook posts.")
except Exception as e:
    print(f"Error updating index.html: {e}")

if blog_posts_html:
    print("4. Updating blog.html...")
    try:
        if os.path.exists('blog.html'):
            with open('blog.html', 'r', encoding='utf-8') as f:
                bhtml = f.read()

            bpattern = re.compile(r'(<!-- AUTOMATIC_BLOG_INSERTION_POINT -->)(.*?)(</div>\s*</main>)', re.DOTALL)
            b_new_html = bpattern.sub(r'\1\n' + "\n".join(blog_posts_html) + r'\n\3', bhtml)
            
            with open('blog.html', 'w', encoding='utf-8') as f:
                f.write(b_new_html)
                
            print("Success! blog.html has been updated.")
        else:
            print("blog.html not found, skipping blog update.")
    except Exception as e:
        print(f"Error updating blog.html: {e}")
        exit(1)
