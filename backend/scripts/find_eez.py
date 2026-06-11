import urllib.request
import json

def fetch_eez():
    print("Searching GitHub for EEZ geojson...")
    url = "https://api.github.com/search/code?q=eez+extension:geojson+size:>10000"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            items = data.get("items", [])
            print(f"Found {len(items)} results.")
            for item in items[:5]:
                repo = item['repository']['full_name']
                path = item['path']
                print(f"Repo: {repo}, Path: {path}")
                raw_url = f"https://raw.githubusercontent.com/{repo}/main/{path}"
                print(f"Try URL: {raw_url}")
                raw_url2 = f"https://raw.githubusercontent.com/{repo}/master/{path}"
                print(f"Try URL2: {raw_url2}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    fetch_eez()
