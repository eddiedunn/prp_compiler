import json
import urllib.parse
import urllib.request
import re


def run(query: str, max_results: int = 5) -> str:
    """Perform a simple DuckDuckGo search and return formatted results."""
    params = urllib.parse.urlencode({"q": query, "t": "h_", "ia": "web"})
    url = f"https://duckduckgo.com/html/?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            html = resp.read().decode()
    except Exception as e:
        return f"[ERROR] Failed to fetch search results: {e}"

    pattern = re.compile(r'class="result__a" href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>')
    results = []
    for match in pattern.finditer(html):
        title = re.sub("<.*?>", "", match.group("title"))
        href = match.group("href")
        results.append(f"{title} - {href}")
        if len(results) >= max_results:
            break

    return "\n".join(results)
