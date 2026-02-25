import requests

from .http import build_note_api_headers
from .markdown import markdown_body_length, markdown_to_html


def create_article(cookies, title, markdown_content):
    """新しい記事を作成"""
    html_content = markdown_to_html(markdown_content)

    headers = build_note_api_headers(cookies)
    data = {
        "body": html_content,
        "name": title,
    }

    response = requests.post(
        "https://note.com/api/v1/text_notes",
        cookies=cookies,
        headers=headers,
        json=data,
    )

    if response.status_code in (200, 201):
        result = response.json()
        payload = result.get("data", {})
        article_id = payload.get("id")
        article_key = payload.get("key")
        if not article_id or not article_key:
            print("記事作成失敗: レスポンスに記事ID/KEYがありません")
            print(f"レスポンス本文: {response.text[:500]}")
            return None, None
        print(f"記事作成成功！ID: {article_id}")
        print(f"記事作成レスポンス data keys: {list(payload.keys())}")
        return article_id, article_key

    print(f"記事作成失敗: {response.status_code}")
    print(f"レスポンス本文: {response.text[:500]}")
    return None, None


def update_article_draft(
    cookies,
    article_id,
    article_key,
    title,
    markdown_content,
    image_key=None,
    embedded_image_keys=None,
):
    """記事を更新して下書き保存"""
    embedded_image_keys = list(dict.fromkeys(embedded_image_keys or []))
    headers = build_note_api_headers(cookies)
    url = "https://note.com/api/v1/text_notes/draft_save"
    html_content = markdown_to_html(markdown_content)
    body_length = markdown_body_length(markdown_content)

    payload_candidates = [
        {
            "name": title,
            "body": html_content,
            "body_length": body_length,
            "index": False,
            "is_lead_form": False,
            "raw_body": markdown_content,
            "image_keys": embedded_image_keys,
            "embedded_image_keys": embedded_image_keys,
        },
        {
            "name": title,
            "body": html_content,
            "body_length": body_length,
            "index": False,
            "is_lead_form": False,
        },
        {
            "name": title,
            "body": markdown_content,
            "body_length": body_length,
            "index": False,
            "is_lead_form": False,
        },
        {"id": article_id, "name": title, "body": html_content},
        {"key": article_key, "name": title, "body": html_content},
    ]

    if image_key:
        for payload in payload_candidates:
            payload["eyecatch_image_key"] = image_key

    last_response = None
    for idx, payload in enumerate(payload_candidates, 1):
        response = requests.post(
            url,
            cookies=cookies,
            headers=headers,
            params={"id": article_id, "is_temp_saved": "true"},
            json=payload,
        )
        last_response = response
        if response.status_code in (200, 201):
            print(f"記事の下書き保存成功！(POST draft_save / pattern {idx})")
            return True

    if last_response is not None:
        print(f"記事の更新失敗: {last_response.status_code}")
        print(f"レスポンス本文: {last_response.text[:500]}")
    else:
        print("記事の更新失敗: リクエストが実行されませんでした")
    return False
