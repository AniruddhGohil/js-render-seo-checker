def compare_elements(raw: dict, rendered: dict) -> dict:
    issues = []

    def _add(element, severity, issue, raw_val, rendered_val):
        issues.append({
            "element": element,
            "severity": severity,
            "issue": issue,
            "raw": str(raw_val) if raw_val is not None else "Missing",
            "rendered": str(rendered_val) if rendered_val is not None else "Missing",
        })

    # Title
    if not raw.get("title") and rendered.get("title"):
        _add("Title", "Critical", "Title only present after JS rendering",
             "Missing", rendered["title"])
    elif raw.get("title") != rendered.get("title") and rendered.get("title"):
        _add("Title", "Medium", "Title differs between raw and rendered",
             raw["title"], rendered["title"])

    # Meta description
    if not raw.get("meta_description") and rendered.get("meta_description"):
        _add("Meta Description", "High",
             "Meta description only present after JS rendering",
             "Missing", rendered["meta_description"][:120])

    # Canonical
    if not raw.get("canonical") and rendered.get("canonical"):
        _add("Canonical", "High", "Canonical tag only present after JS rendering",
             "Missing", rendered["canonical"])

    # H1
    raw_h1s = set(raw.get("h1", []))
    rendered_h1s = set(rendered.get("h1", []))
    missing_h1s = rendered_h1s - raw_h1s
    if not raw.get("h1") and rendered.get("h1"):
        _add("H1", "Critical", "H1 tag only present after JS rendering",
             "None found", "; ".join(list(rendered_h1s)[:3]))
    elif missing_h1s:
        _add("H1", "High", f"{len(missing_h1s)} H1(s) only visible after rendering",
             f"{len(raw_h1s)} found", f"{len(rendered_h1s)} found")

    # Internal links
    raw_urls = {l["url"] for l in raw.get("internal_links", [])}
    rendered_urls = {l["url"] for l in rendered.get("internal_links", [])}
    js_only_links = rendered_urls - raw_urls
    if js_only_links:
        _add("Internal Links", "Medium",
             f"{len(js_only_links)} internal link(s) only discoverable after JS rendering",
             f"{len(raw_urls)} links",
             f"{len(rendered_urls)} links (+{len(js_only_links)} JS-only)")

    # Structured data
    if not raw.get("structured_data") and rendered.get("structured_data"):
        _add("Structured Data", "Medium",
             "JSON-LD only present after JS rendering",
             "None found",
             f"{len(rendered['structured_data'])} schema(s) found")

    # Content / word count
    raw_words = raw.get("word_count", 0)
    rendered_words = rendered.get("word_count", 0)
    if rendered_words > 0:
        js_dep_pct = ((rendered_words - raw_words) / rendered_words) * 100
    else:
        js_dep_pct = 0.0

    if js_dep_pct > 20:
        sev = "Critical" if js_dep_pct > 60 else "High" if js_dep_pct > 40 else "Medium"
        _add("Content", sev,
             f"{js_dep_pct:.1f}% of page content depends on JavaScript",
             f"{raw_words:,} words", f"{rendered_words:,} words")

    # SEO score (simple deduction model)
    deductions = {"Critical": 25, "High": 15, "Medium": 8, "Low": 3}
    total_deduction = sum(deductions.get(i["severity"], 0) for i in issues)
    seo_score = max(0, 100 - total_deduction)

    new_internal_links = [
        l for l in rendered.get("internal_links", []) if l["url"] not in raw_urls
    ]

    return {
        "issues": issues,
        "issue_count": len(issues),
        "js_dependency_score": round(js_dep_pct, 1),
        "seo_score": seo_score,
        "new_internal_links": new_internal_links,
    }
