import json
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def extract_seo_elements(html: str, base_url: str = "") -> dict:
    soup = BeautifulSoup(html, "lxml")

    # Word count from visible text
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    body_text = soup.get_text(separator=" ")
    words = [w for w in body_text.split() if w.strip()]

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    meta_desc = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_desc.get("content", "").strip() if meta_desc else None

    meta_robots = soup.find("meta", attrs={"name": "robots"})
    robots = meta_robots.get("content", "").strip() if meta_robots else None

    canonical_tag = soup.find("link", rel="canonical")
    canonical = canonical_tag.get("href", "").strip() if canonical_tag else None

    h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3_tags = [h.get_text(strip=True) for h in soup.find_all("h3")]

    base_domain = urlparse(base_url).netloc if base_url else ""
    internal_links, external_links = [], []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        anchor = a.get_text(strip=True)
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full_url = urljoin(base_url, href) if base_url else href
        link_domain = urlparse(full_url).netloc
        entry = {"url": full_url, "anchor": anchor, "raw_href": href}
        if base_domain and link_domain == base_domain:
            internal_links.append(entry)
        elif link_domain:
            external_links.append(entry)

    structured_data = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            structured_data.append(data)
        except (json.JSONDecodeError, TypeError):
            pass

    images = [
        {"src": img.get("src", ""), "alt": img.get("alt", ""), "has_alt": bool(img.get("alt", ""))}
        for img in soup.find_all("img")
    ]

    og_tags = {}
    for meta in soup.find_all("meta"):
        prop = meta.get("property", "") or meta.get("name", "")
        if prop.startswith("og:"):
            og_tags[prop] = meta.get("content", "")

    return {
        "title": title,
        "meta_description": meta_description,
        "robots": robots,
        "canonical": canonical,
        "h1": h1_tags,
        "h2": h2_tags,
        "h3": h3_tags,
        "internal_links": internal_links,
        "external_links": external_links,
        "internal_link_count": len(internal_links),
        "external_link_count": len(external_links),
        "structured_data": structured_data,
        "images": images,
        "image_count": len(images),
        "images_without_alt": len([i for i in images if not i["has_alt"]]),
        "og_tags": og_tags,
        "word_count": len(words),
        "char_count": len(body_text),
    }
