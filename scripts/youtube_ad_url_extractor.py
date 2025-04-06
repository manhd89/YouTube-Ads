#!/usr/bin/env python3
import os
import re
import sys
import http.client
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# Cấu hình
URLS_FILE = "youtube_urls.txt"
OUTPUT_FILE = "youtube_ad_urls.txt"
MAX_WORKERS = 5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
TIMEOUT = 30

def is_ad_url(url):
    ad_keywords = ['ctier', 'oad', 'videoplayback', 'adformat']
    return any(keyword in url.lower() for keyword in ad_keywords)

def extract_domain(url):
    try:
        return urlparse(url).netloc
    except:
        return url

def load_existing_domains():
    domains = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    domain = line.split('.')[-1].strip() if line[0].isdigit() else line
                    domains.add(domain)
    return domains

def fetch_url_content(url):
    parsed = urllib.parse.urlparse(url)
    conn = http.client.HTTPSConnection(parsed.netloc, timeout=TIMEOUT) if parsed.scheme == 'https' else http.client.HTTPConnection(parsed.netloc, timeout=TIMEOUT)
    
    path = parsed.path
    if parsed.query:
        path += '?' + parsed.query
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    try:
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        if response.status == 200:
            return response.read().decode('utf-8')
        else:
            print(f"[ERROR] HTTP {response.status} khi truy cập {url}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"[ERROR] Lỗi kết nối đến {url}: {str(e)}", file=sys.stderr)
        return None
    finally:
        conn.close()

def process_single_url(youtube_url):
    try:
        content = fetch_url_content(youtube_url)
        if not content:
            return set()
        
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+googlevideo\.com[^\s"\']*'
        found_urls = re.findall(url_pattern, content)
        
        return {extract_domain(url) for url in found_urls if is_ad_url(url)}
    except Exception as e:
        print(f"[ERROR] Lỗi khi xử lý {youtube_url}: {str(e)}", file=sys.stderr)
        return set()

def process_multiple_urls(urls):
    new_domains = set()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_url, url): url for url in urls}
        
        for future in as_completed(futures):
            url = futures[future]
            try:
                domains = future.result()
                new_domains.update(domains)
                print(f"[OK] Đã xử lý: {url} ({len(domains)} domain mới)")
            except Exception as e:
                print(f"[ERROR] Lỗi khi xử lý {url}: {str(e)}", file=sys.stderr)
    
    return new_domains

def load_youtube_urls():
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return []

def save_domains(domains):
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for domain in sorted(domains):
                f.write(f"{domain}\n")
        return True
    except Exception as e:
        print(f"[ERROR] Lỗi khi ghi file: {str(e)}", file=sys.stderr)
        return False

def main():
    existing_domains = load_existing_domains()
    print(f"Đã tải {len(existing_domains)} domain từ file hiện có")

    youtube_urls = load_youtube_urls()
    
    if not youtube_urls:
        print("Không tìm thấy URLs trong youtube_urls.txt")
        return
    
    print(f"Bắt đầu xử lý {len(youtube_urls)} URLs YouTube...")
    new_domains = process_multiple_urls(youtube_urls)
    
    all_domains = existing_domains.union(new_domains)
    print(f"\nTổng kết:")
    print(f"- Domain hiện có: {len(existing_domains)}")
    print(f"- Domain mới: {len(new_domains)}")
    print(f"- Tổng cộng: {len(all_domains)}")

    save_domains(all_domains)

if __name__ == "__main__":
    main()
