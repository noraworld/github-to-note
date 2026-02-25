def build_note_api_headers(cookies):
    """note API向けヘッダーを組み立てる"""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://editor.note.com",
        "Referer": "https://editor.note.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    csrf_token = (
        cookies.get("csrf_token")
        or cookies.get("_csrf_token")
        or cookies.get("XSRF-TOKEN")
        or cookies.get("xsrf-token")
    )
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
        headers["X-XSRF-TOKEN"] = csrf_token

    return headers
