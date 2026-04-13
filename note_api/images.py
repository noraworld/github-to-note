import mimetypes
import os
import re
import tempfile
import time
from urllib.parse import urlparse

import requests
from PIL import Image


def check_url_status(url):
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        return resp.status_code
    except requests.RequestException:
        return "ERR"


def _parse_eyecatch_ratio_error(resp):
    try:
        payload = resp.json()
    except ValueError:
        return None

    if not isinstance(payload, dict):
        return None

    error = payload.get("error")
    if not isinstance(error, dict):
        return None

    message = str(error.get("message") or "").strip()
    if not message:
        return None

    match = re.search(r"(\d+)\s*:\s*(\d+)", message)
    if not match:
        return None

    width_ratio = int(match.group(1))
    height_ratio = int(match.group(2))
    if width_ratio <= 0 or height_ratio <= 0:
        return None

    return {
        "code": error.get("code"),
        "message": message,
        "width_ratio": width_ratio,
        "height_ratio": height_ratio,
    }


def _center_crop_to_ratio(image_path, width_ratio, height_ratio):
    with Image.open(image_path) as img:
        src_width, src_height = img.size
        target_ratio = width_ratio / height_ratio
        src_ratio = src_width / src_height

        if abs(src_ratio - target_ratio) < 1e-6:
            return image_path

        if src_ratio > target_ratio:
            crop_width = max(1, int(round(src_height * target_ratio)))
            crop_height = src_height
        else:
            crop_width = src_width
            crop_height = max(1, int(round(src_width / target_ratio)))

        left = max(0, (src_width - crop_width) // 2)
        top = max(0, (src_height - crop_height) // 2)
        right = left + crop_width
        bottom = top + crop_height

        cropped = img.crop((left, top, right, bottom))
        suffix = os.path.splitext(image_path)[1] or ".jpg"
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=suffix).name
        save_image = cropped
        if save_image.mode not in ("RGB", "RGBA", "L"):
            save_image = save_image.convert("RGB")
        if suffix.lower() in (".jpg", ".jpeg") and save_image.mode == "RGBA":
            save_image = save_image.convert("RGB")
        save_image.save(temp_path)
        return temp_path


def upload_image(cookies, image_path):
    """note v3 presigned_post で画像をアップロード"""
    filename = os.path.basename(image_path)
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
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

    presign_resp = requests.post(
        "https://note.com/api/v3/images/upload/presigned_post",
        cookies=cookies,
        headers=headers,
        files={"filename": (None, filename)},
        timeout=30,
    )
    if presign_resp.status_code not in (200, 201):
        print(f"画像アップロード失敗(署名取得): {presign_resp.status_code}")
        print(f"レスポンス本文: {presign_resp.text[:500]}")
        return None, None

    try:
        presign_json = presign_resp.json()
    except ValueError:
        print("画像アップロード失敗: 署名取得レスポンスがJSONではありません")
        return None, None

    data = presign_json.get("data", {})
    upload_url = data.get("action")
    post_fields = data.get("post", {})
    image_url = data.get("url")
    image_key = data.get("path")

    if not upload_url or not post_fields:
        print("画像アップロード失敗: 署名情報が不足しています")
        print(f"レスポンス本文: {presign_resp.text[:500]}")
        return None, None

    s3_headers = {
        "User-Agent": headers["User-Agent"],
        "Accept": "*/*",
        "Origin": "https://editor.note.com",
        "Referer": "https://editor.note.com/",
    }
    with open(image_path, "rb") as f:
        s3_resp = requests.post(
            upload_url,
            data=post_fields,
            files={"file": (filename, f, mime_type)},
            headers=s3_headers,
            timeout=60,
        )

    if s3_resp.status_code != 204:
        print(f"画像アップロード失敗(S3): {s3_resp.status_code}")
        print(f"レスポンス本文: {s3_resp.text[:500]}")
        return None, None

    print("画像アップロード成功！(v3 presigned_post)")
    if image_url:
        status = check_url_status(image_url)
        print(f"アップロード画像URL到達確認: {status} ({image_url})")
    return image_key, image_url


def upload_image_from_url(cookies, image_url):
    """外部画像URLをダウンロードしてnoteへアップロード"""
    try:
        response = requests.get(
            image_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"画像ダウンロード失敗: {image_url} ({exc})")
        return None, None

    ext = os.path.splitext(urlparse(image_url).path)[1]
    if not ext:
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        ext = mimetypes.guess_extension(content_type) or ".jpg"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(response.content)
            temp_path = tmp.name

        uploaded_key, uploaded_url = upload_image(cookies, temp_path)
        return uploaded_key, uploaded_url
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def upload_markdown_images(cookies, markdown_content):
    """本文内の Markdown 画像を note へアップロードし URL を差し替える"""
    pattern = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)")
    matches = pattern.findall(markdown_content)
    if not matches:
        return markdown_content, []

    url_map = {}
    key_list = []
    for _, src_url in matches:
        if src_url in url_map:
            continue
        uploaded_key, uploaded_url = upload_image_from_url(cookies, src_url)
        if uploaded_url:
            url_map[src_url] = uploaded_url
            if uploaded_key:
                key_list.append(uploaded_key)
        else:
            print(f"画像URLの置換をスキップ（元URL維持）: {src_url}")

    if not url_map:
        return markdown_content, []

    def replace_image(match):
        alt = match.group(1)
        src_url = match.group(2)
        new_url = url_map.get(src_url, src_url)
        return f"![{alt}]({new_url})"

    replaced = pattern.sub(replace_image, markdown_content)
    unique_keys = list(dict.fromkeys(key_list))
    if unique_keys:
        print(f"本文画像キー: {unique_keys}")
    return replaced, unique_keys


def upload_note_eyecatch(cookies, note_id, image_path):
    """サムネイル画像を note_eyecatch エンドポイントへアップロード"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
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

    filename = os.path.basename(image_path)
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    file_variants = [
        ("file", ("blob", None, mime_type)),
        ("file", (filename, None, mime_type)),
        ("image", ("blob", None, mime_type)),
    ]

    last_resp = None
    for attempt in range(1, 4):
        for file_key, file_meta in file_variants:
            with open(image_path, "rb") as f:
                upload_name, _, content_type = file_meta
                files = {file_key: (upload_name, f, content_type)}
                resp = requests.post(
                    "https://note.com/api/v1/image_upload/note_eyecatch",
                    cookies=cookies,
                    headers=headers,
                    files=files,
                    data={"note_id": str(note_id)},
                    timeout=60,
                )
            last_resp = resp
            if resp.status_code in (200, 201):
                try:
                    payload = resp.json()
                except ValueError:
                    payload = {}
                data = payload.get("data", {}) if isinstance(payload, dict) else {}
                eyecatch_url = data.get("url")
                eyecatch_key = (
                    data.get("key")
                    or data.get("image_key")
                    or data.get("eyecatch_image_key")
                    or data.get("path")
                )
                if eyecatch_url or eyecatch_key:
                    print(
                        "サムネイル画像アップロード成功: "
                        f"url={eyecatch_url}, key={eyecatch_key}, data_keys={list(data.keys())}"
                    )
                    return {
                        "success": True,
                        "url": eyecatch_url,
                        "key": eyecatch_key,
                        "data": data,
                    }
                ratio_error = _parse_eyecatch_ratio_error(resp)
                if ratio_error:
                    print(
                        "サムネイル画像アップロード失敗: "
                        f"{ratio_error['message']} "
                        f"(status={resp.status_code})"
                    )
                    return {
                        "success": False,
                        "error": ratio_error,
                    }
                print(
                    "サムネイル画像アップロード失敗: "
                    f"レスポンスに url/key がありません "
                    f"(status={resp.status_code}, data_keys={list(data.keys())})"
                )
                print(f"レスポンス本文: {resp.text[:500]}")
        time.sleep(1.5 * attempt)

    if last_resp is not None:
        print(f"サムネイル画像アップロード失敗: {last_resp.status_code}")
        print(f"レスポンス本文: {last_resp.text[:500]}")
    else:
        print("サムネイル画像アップロード失敗: リクエスト未実行")
    return None


def upload_note_eyecatch_from_url(cookies, note_id, image_url):
    """外部URLの画像をダウンロードしてサムネイル画像としてアップロード"""
    try:
        response = requests.get(
            image_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"サムネイル画像ダウンロード失敗: {image_url} ({exc})")
        return None

    ext = os.path.splitext(urlparse(image_url).path)[1]
    if not ext:
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        ext = mimetypes.guess_extension(content_type) or ".jpg"

    temp_path = None
    cropped_temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(response.content)
            temp_path = tmp.name
        result = upload_note_eyecatch(cookies, note_id, temp_path)
        if result and result.get("success"):
            return result

        ratio_error = result.get("error") if isinstance(result, dict) else None
        if ratio_error and ratio_error.get("width_ratio") and ratio_error.get("height_ratio"):
            width_ratio = ratio_error["width_ratio"]
            height_ratio = ratio_error["height_ratio"]
            print(
                "サムネイル画像を中央クロップして再試行: "
                f"{width_ratio}:{height_ratio}"
            )
            cropped_temp_path = _center_crop_to_ratio(temp_path, width_ratio, height_ratio)
            retry_result = upload_note_eyecatch(cookies, note_id, cropped_temp_path)
            if retry_result and retry_result.get("success"):
                return retry_result
            return None

        return None
    finally:
        if cropped_temp_path and cropped_temp_path != temp_path and os.path.exists(cropped_temp_path):
            os.remove(cropped_temp_path)
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
