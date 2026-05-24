import requests
import time

GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
NORMAL_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def fetch_raw_html(url: str, use_googlebot: bool = False, timeout: int = 30) -> dict:
    ua = GOOGLEBOT_UA if use_googlebot else NORMAL_UA
    headers = {"User-Agent": ua}

    start = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        fetch_time = round(time.time() - start, 2)
        return {
            "html": response.text,
            "status_code": response.status_code,
            "fetch_time": fetch_time,
            "final_url": response.url,
            "content_length": len(response.text),
            "response_headers": dict(response.headers),
        }
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection error: {e}"}
    except requests.exceptions.Timeout:
        return {"error": f"Request timed out after {timeout}s"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
