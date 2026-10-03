from engine import safe_get, parse_public_page

def research_url(url):
    r = safe_get(url)
    if not r:
        return {"status": "INDISPONÍVEL", "text": ""}
    return {"status": "OK", "text": parse_public_page(r.text)}
