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


def update_existing_article(cookies, article_id, title, markdown_content):
    """既存記事の存在確認のみ行い、本文更新は draft_save 側で実施"""
    headers = build_note_api_headers(cookies)
    response = requests.get(
        f"https://note.com/api/v1/text_notes/{article_id}",
        cookies=cookies,
        headers=headers,
    )

    if response.status_code == 404:
        print(f"既存記事の取得失敗: {response.status_code}")
        print(f"レスポンス本文: {response.text[:500]}")
        print("article_id が存在しないため更新を中断します。")
        return None, None, False

    if response.status_code == 405:
        print("既存記事の事前確認は 405 のためスキップします。draft_save で更新します。")
        return article_id, None, False

    if response.status_code not in (200, 201):
        print(f"既存記事の確認に失敗: {response.status_code}")
        print(f"レスポンス本文: {response.text[:500]}")
        print("article_id の確認ができないため更新を中断します。")
        return None, None, False

    print("既存記事の確認成功。draft_save で更新します。")
    return article_id, None, False


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
            try:
                resp_json = response.json()
            except Exception:
                resp_json = {}

            error = resp_json.get("error") if isinstance(resp_json, dict) else None
            if error:
                code = error.get("code", "unknown")
                message = error.get("message", "")
                if code == "invalid" and "cannot edit others draft" in message:
                    print("記事の更新失敗: 指定した article_id は編集できません（存在しないか、権限がありません）。")
                else:
                    print(f"記事の更新失敗: APIエラー code={code}, message={message}")
                return False
            print(f"記事の下書き保存成功！(POST draft_save / pattern {idx})")
            return True

    if last_response is not None:
        print(f"記事の更新失敗: {last_response.status_code}")
        print(f"レスポンス本文: {last_response.text[:500]}")
    else:
        print("記事の更新失敗: リクエストが実行されませんでした")
    return False


def publish_article(
    cookies,
    article_id,
    title,
    markdown_content,
    hashtags=None,
    article_key=None,
    embedded_image_keys=None,
):
    """記事を公開する"""
    headers = build_note_api_headers(cookies)
    html_content = markdown_to_html(markdown_content)
    body_length = markdown_body_length(markdown_content)
    normalized_hashtags = []
    for tag in hashtags or []:
        value = str(tag).strip()
        if not value:
            continue
        if not value.startswith("#"):
            value = f"#{value}"
        normalized_hashtags.append(value)

    payload = {
        "author_ids": [],
        "body_length": body_length,
        "disable_comment": False,
        "exclude_from_creator_top": False,
        "exclude_ai_learning_reward": False,
        "free_body": html_content,
        "hashtags": normalized_hashtags,
        "image_keys": list(dict.fromkeys(embedded_image_keys or [])),
        "index": False,
        "is_refund": False,
        "limited": False,
        "magazine_ids": [],
        "magazine_keys": [],
        "name": title,
        "pay_body": "",
        "price": 0,
        "send_notifications_flag": True,
        "separator": None,
        "status": "published",
        "circle_permissions": [],
        "discount_campaigns": [],
        "lead_form": {"is_active": False, "consent_url": ""},
        "line_add_friend": {"is_active": False, "keyword": "", "add_friend_url": ""},
    }
    if article_key:
        payload["slug"] = f"slug-{article_key}"

    response = requests.put(
        f"https://note.com/api/v1/text_notes/{article_id}",
        cookies=cookies,
        headers=headers,
        json=payload,
    )
    if response.status_code not in (200, 201):
        print(f"記事の公開失敗: {response.status_code}")
        print(f"レスポンス本文: {response.text[:500]}")
        return False

    try:
        resp_json = response.json()
    except Exception:
        resp_json = {}
    error = resp_json.get("error") if isinstance(resp_json, dict) else None
    if error:
        code = error.get("code", "unknown")
        message = error.get("message", "")
        print(f"記事の公開失敗: APIエラー code={code}, message={message}")
        return False

    print("記事の公開成功！")
    return True
