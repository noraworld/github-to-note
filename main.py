from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import mimetypes
import tempfile
import uuid
from urllib.parse import urlparse

def get_note_cookies(email, password):
    """noteにログインしてCookieを取得"""
    driver = webdriver.Chrome()

    try:
        # ログインページにアクセス
        driver.get("https://note.com/login")
        wait = WebDriverWait(driver, 20)

        def find_first(selectors):
            for by, value in selectors:
                elements = driver.find_elements(by, value)
                if elements:
                    return elements[0]
            return None

        # 「メールアドレスでログイン」導線がある場合は開く
        email_login_entry = find_first([
            (By.XPATH, "//a[contains(., 'メールアドレス') and contains(., 'ログイン')]"),
            (By.XPATH, "//button[contains(., 'メールアドレス') and contains(., 'ログイン')]"),
            (By.XPATH, "//a[contains(., 'メールアドレスでログイン')]"),
            (By.XPATH, "//button[contains(., 'メールアドレスでログイン')]"),
        ])
        if email_login_entry:
            wait.until(EC.element_to_be_clickable(email_login_entry)).click()

        # メールアドレス欄とパスワード欄を柔軟に探索
        wait.until(
            lambda d: find_first([
                (By.NAME, "email"),
                (By.NAME, "login"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[autocomplete='username']"),
                (By.XPATH, "//input[contains(@placeholder, 'メール')]"),
            ]) is not None
        )
        email_input = find_first([
            (By.NAME, "email"),
            (By.NAME, "login"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[autocomplete='username']"),
            (By.XPATH, "//input[contains(@placeholder, 'メール')]"),
        ])
        if not email_input:
            raise TimeoutException("メールアドレス入力欄を検出できませんでした。")

        password_input = find_first([
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
            (By.XPATH, "//input[contains(@placeholder, 'パスワード')]"),
        ])
        if not password_input:
            raise TimeoutException("パスワード入力欄を検出できませんでした。")

        email_input.clear()
        email_input.send_keys(email)
        password_input.clear()
        password_input.send_keys(password)

        login_button = find_first([
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//button[contains(., 'ログイン')]"),
            (By.XPATH, "//button[contains(., 'Sign in')]"),
            (By.XPATH, "//input[@type='submit']"),
        ])
        if not login_button:
            raise TimeoutException("ログインボタンを検出できませんでした。")
        wait.until(EC.element_to_be_clickable(login_button)).click()

        # ログイン後のURL遷移を待機
        wait.until(lambda d: "note.com/login" not in d.current_url)
        time.sleep(2)

        # Cookieを取得
        cookies = driver.get_cookies()

        # Cookie辞書に変換
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie['name']] = cookie['value']

        return cookie_dict

    except (TimeoutException, NoSuchElementException) as exc:
        print(f"ログイン処理で要素取得に失敗しました: {exc}")
        return {}
    finally:
        driver.quit()

import requests

def build_note_api_headers(cookies):
    """note API向けヘッダーを組み立てる"""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://editor.note.com",
        "Referer": "https://editor.note.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    # 422 (CSRF) 対策: Cookie内のトークン候補をヘッダーに付与
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

def create_article(cookies, title, markdown_content):
    """新しい記事を作成"""

    # MarkdownをHTMLに変換（簡易版）
    html_content = markdown_to_html(markdown_content)

    headers = build_note_api_headers(cookies)

    data = {
        "body": html_content,
        "name": title,
    }

    response = requests.post(
        'https://note.com/api/v1/text_notes',
        cookies=cookies,
        headers=headers,
        json=data
    )

    if response.status_code in (200, 201):
        result = response.json()
        data = result.get("data", {})
        note_data = data.get("note", {}) if isinstance(data.get("note"), dict) else {}
        article_id = data.get("id")
        article_key = data.get("key")
        article_meta = {
            "article_id": article_id,
            "note_id": note_data.get("id") or data.get("note_id"),
            "note_key": note_data.get("key") or data.get("note_key") or article_key,
            "created_at": data.get("created_at"),
            "last_updated_at": data.get("last_updated_at") or note_data.get("last_updated_at"),
        }
        print(f"記事作成成功！ID: {article_id}")
        print(f"記事作成レスポンス data keys: {list(data.keys())}")
        if article_meta["note_id"] or article_meta["last_updated_at"]:
            print(
                f"記事メタ: note_id={article_meta['note_id']}, "
                f"last_updated_at={article_meta['last_updated_at']}"
            )
        return article_id, article_key, article_meta
    else:
        print(f"記事作成失敗: {response.status_code}")
        print(f"レスポンス本文: {response.text[:500]}")
        return None, None, {}

def post_to_note(email, password, title, markdown_content, image_path=None):
    """noteに記事を投稿する完全な関数"""

    print("1. noteにログイン中...")
    cookies = get_note_cookies(email, password)

    print("2. 本文中の画像をアップロード中...")
    processed_markdown, embedded_image_keys = upload_markdown_images(cookies, markdown_content)

    print("3. 記事を作成中...")
    article_id, article_key, article_meta = create_article(cookies, title, processed_markdown)

    if not article_id:
        return False

    image_key = None
    if image_path:
        print("4. 画像をアップロード中...")
        # image_key, image_url = upload_image(cookies, image_path)

    # create_article直後は本文が反映されないケースがあるため、必ず更新を実行する
    print("5. 記事を下書き保存中...")
    success = update_article_draft(
        cookies,
        article_id,
        article_key,
        title,
        processed_markdown,
        image_key,
        embedded_image_keys,
        article_meta
    )
    if not success:
        return False

    print(f"\n✅ 投稿完了！")
    print(f"記事URL: https://note.com/your_username/n/{article_key}")
    return True

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

    # 1) note API から presigned POST 情報を取得
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
    s3_key = post_fields.get("key") or image_key

    if not upload_url or not post_fields:
        print("画像アップロード失敗: 署名情報が不足しています")
        print(f"レスポンス本文: {presign_resp.text[:500]}")
        return None, None

    # 2) 取得したS3 presigned POSTへ実ファイルをアップロード
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
    # noteが返す data.url(assets.st-note.com) を優先利用
    return image_key, image_url


def check_url_status(url):
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        return resp.status_code
    except requests.RequestException:
        return "ERR"


def upload_image_from_url(cookies, image_url):
    """外部画像URLをダウンロードしてnoteへアップロード"""
    try:
        response = requests.get(
            image_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"画像ダウンロード失敗: {image_url} ({exc})")
        return None

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


def normalize_image_keys(keys):
    """editor互換性のため key の表現ゆれを吸収"""
    normalized = []
    for key in keys:
        if not key:
            continue
        k = key.strip()
        if not k:
            continue
        normalized.append(k)
        # img/123.jpg -> 123.jpg の形も併記
        if "/" in k:
            normalized.append(k.split("/")[-1])
    return list(dict.fromkeys(normalized))

def update_article_draft(
    cookies,
    article_id,
    article_key,
    title,
    markdown_content,
    image_key=None,
    embedded_image_keys=None,
    article_meta=None
):
    """記事を更新して下書きとして保存"""

    embedded_image_keys = list(dict.fromkeys(embedded_image_keys or []))
    headers = build_note_api_headers(cookies)
    url = "https://note.com/api/v1/text_notes/draft_save"
    html_content = markdown_to_html(markdown_content)
    body_length = markdown_body_length(markdown_content)

    # 表示はHTML、編集はMarkdownを使えるよう両方を送る
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
            if "text_note" in payload:
                payload["text_note"]["eyecatch_image_key"] = image_key
            else:
                payload["eyecatch_image_key"] = image_key

    last_response = None
    for idx, payload in enumerate(payload_candidates, 1):
        response = requests.post(
            url,
            cookies=cookies,
            headers=headers,
            params={"id": article_id, "is_temp_saved": "true"},
            json=payload
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


def verify_latest_draft_version(cookies, article_key, article_meta):
    """v3のversion_verificationを呼び出して整合性確認"""
    headers = build_note_api_headers(cookies)
    article_meta = article_meta or {}
    article_id = article_meta.get("article_id")
    last_updated_at = article_meta.get("last_updated_at")

    discovered_note_refs = []

    # createレスポンスで不足している場合は text_note 取得で補完を試す
    if (not last_updated_at or not article_meta.get("note_id")) and article_id:
        try:
            resp = requests.get(
                f"https://note.com/api/v1/text_notes/{article_id}",
                cookies=cookies,
                headers=headers,
                timeout=20,
            )
            if resp.status_code == 200:
                json_body = resp.json()
                data = json_body.get("data", {})
                note_obj = data.get("note", {}) if isinstance(data.get("note"), dict) else {}
                article_meta["note_id"] = article_meta.get("note_id") or note_obj.get("id") or data.get("note_id")
                article_meta["note_key"] = article_meta.get("note_key") or note_obj.get("key") or data.get("note_key")
                discovered_note_refs.extend(extract_note_refs(json_body))
                last_updated_at = (
                    last_updated_at
                    or data.get("last_updated_at")
                    or data.get("updated_at")
                    or note_obj.get("last_updated_at")
                )
                article_meta["last_updated_at"] = last_updated_at
                print(
                    "text_note取得でメタ補完: "
                    f"note_id={article_meta.get('note_id')}, "
                    f"note_key={article_meta.get('note_key')}, "
                    f"last_updated_at={last_updated_at}"
                )
        except requests.RequestException:
            pass

    note_refs = [
        *discovered_note_refs,
        article_meta.get("note_id"),
        article_meta.get("note_key"),
        article_key,
    ]
    note_refs = [n for n in note_refs if n]
    note_refs = list(dict.fromkeys(note_refs))
    if discovered_note_refs:
        print(f"抽出note_ref候補: {list(dict.fromkeys(discovered_note_refs))}")

    # last_updated_at がない場合は latest_draft から取得を試行
    if note_refs and not last_updated_at:
        for note_ref in note_refs:
            latest_draft_urls = [
                f"https://note.com/api/v3/notes/{note_ref}/latest_draft",
                f"https://note.com/api/v3/notes/{note_ref}",
            ]
            for url in latest_draft_urls:
                try:
                    resp = requests.get(
                        url,
                        cookies=cookies,
                        headers=headers,
                        timeout=20,
                    )
                except requests.RequestException:
                    continue
                if resp.status_code != 200:
                    continue
                try:
                    json_body = resp.json()
                    data = json_body.get("data", {})
                except ValueError:
                    data = {}
                    json_body = {}
                extracted = extract_note_refs(json_body)
                if extracted:
                    for ref in extracted:
                        if ref not in note_refs:
                            note_refs.append(ref)
                    print(f"latest_draft応答からnote_ref追加: {extracted}")
                candidate = (
                    data.get("last_updated_at")
                    or (data.get("latest_draft", {}) if isinstance(data.get("latest_draft"), dict) else {}).get("last_updated_at")
                    or data.get("updated_at")
                )
                if candidate:
                    last_updated_at = candidate
                    article_meta["last_updated_at"] = candidate
                    print(f"latest_draft取得で last_updated_at 補完: {note_ref} -> {candidate}")
                    break
            if last_updated_at:
                break

    # 最後のフォールバックとして created_at を使う
    if not last_updated_at and article_meta.get("created_at"):
        last_updated_at = article_meta.get("created_at")
        article_meta["last_updated_at"] = last_updated_at
        print(f"created_at を last_updated_at として使用: {last_updated_at}")

    if not note_refs or not last_updated_at:
        print(
            "version_verificationスキップ: "
            f"note_refs={note_refs}, last_updated_at={last_updated_at}"
        )
        return last_updated_at

    for note_ref in note_refs:
        url = f"https://note.com/api/v3/notes/{note_ref}/latest_draft/version_verification"
        try:
            resp = requests.get(
                url,
                cookies=cookies,
                headers=headers,
                params={"last_updated_at": last_updated_at},
                timeout=20,
            )
        except requests.RequestException:
            continue

        if resp.status_code == 200:
            try:
                data = resp.json().get("data", {})
            except ValueError:
                data = {}
            resolved_ts = data.get("last_updated_at") or last_updated_at
            print(f"version_verification成功: {note_ref}")
            return resolved_ts
        else:
            print(f"version_verification失敗: {note_ref} -> {resp.status_code}")

    print("version_verificationは通りませんでした。既存タイムスタンプで継続します。")
    return last_updated_at


def extract_note_refs(obj):
    """レスポンスJSONから note ref 候補（特に nf...）を抽出"""
    refs = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            s = x.strip()
            if re.match(r"^nf[0-9a-z]+$", s):
                refs.append(s)
            elif re.match(r"^n[0-9a-z]+$", s):
                refs.append(s)
            else:
                m = re.findall(r"/notes/(nf[0-9a-z]+)", s)
                refs.extend(m)
                m2 = re.findall(r"/n/(n[0-9a-z]+)", s)
                refs.extend(m2)

    walk(obj)
    # nf を優先順にする
    refs = list(dict.fromkeys(refs))
    nf_refs = [r for r in refs if r.startswith("nf")]
    n_refs = [r for r in refs if r.startswith("n") and not r.startswith("nf")]
    return nf_refs + n_refs

import re
from html import escape

def markdown_to_html(markdown_text):
    """Markdownをnote表示向けHTMLに変換（見出し/箇条書き/改行対応）"""
    text = markdown_text.replace("\r\n", "\n").strip()
    if not text:
        return ""

    def block_id():
        return str(uuid.uuid4())

    def inline_format(s):
        code_spans = []

        def protect_code(match):
            code_spans.append(f"<code>{escape(match.group(1))}</code>")
            return f"__CODE_SPAN_{len(code_spans) - 1}__"

        s = re.sub(r"`([^`]+)`", protect_code, s)
        s = escape(s)

        def replace_image(match):
            alt = escape(match.group(1).strip())
            url = escape(match.group(2).strip(), quote=True)
            return f'<img src="{url}" alt="{alt}" loading="lazy" class="is-slide" data-modal="true">'

        def replace_link(match):
            label = match.group(1).strip()
            url = escape(match.group(2).strip(), quote=True)
            # ラベル内の簡易装飾も反映
            label = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escape(label))
            label = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", label)
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'

        s = re.sub(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)", replace_image, s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", replace_link, s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)

        for i, code_html in enumerate(code_spans):
            s = s.replace(f"__CODE_SPAN_{i}__", code_html)

        return s

    def image_block(line):
        m = re.match(r"^!\[([^\]]*)\]\((https?://[^)\s]+)\)$", line.strip())
        if not m:
            return None
        alt = escape(m.group(1).strip())
        url = escape(m.group(2).strip(), quote=True)
        bid = block_id()
        return (
            f'<figure name="{bid}" id="{bid}">'
            f'<img src="{url}" alt="{alt}" loading="lazy" class="is-slide" data-modal="true" '
            'contenteditable="false" draggable="false">'
            '<figcaption></figcaption>'
            '</figure>'
        )

    lines = text.split("\n")
    blocks = []
    paragraph_lines = []
    list_items = []
    in_code = False
    code_lines = []

    def flush_paragraph():
        if paragraph_lines:
            paragraph = "<br>".join(inline_format(line) for line in paragraph_lines)
            bid = block_id()
            blocks.append(f'<p name="{bid}" id="{bid}">{paragraph}</p>')
            paragraph_lines.clear()

    def flush_list():
        if list_items:
            items_html = "".join(f"<li>{inline_format(item)}</li>" for item in list_items)
            blocks.append(f"<ul>{items_html}</ul>")
            list_items.clear()

    def flush_code():
        if code_lines:
            code = "\n".join(escape(line) for line in code_lines)
            blocks.append(f"<pre><code>{code}</code></pre>")
            code_lines.clear()

    for raw_line in lines:
        line = raw_line.rstrip()

        if line.strip().startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            flush_list()
            continue

        img_block = image_block(line)
        if img_block is not None:
            flush_paragraph()
            flush_list()
            blocks.append(img_block)
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading_match:
            flush_paragraph()
            flush_list()
            level = len(heading_match.group(1))
            content = inline_format(heading_match.group(2).strip())
            bid = block_id()
            blocks.append(f'<h{level} name="{bid}" id="{bid}">{content}</h{level}>')
            continue

        bullet_match = re.match(r"^[-*]\s+(.+)$", line)
        if bullet_match:
            flush_paragraph()
            list_items.append(bullet_match.group(1).strip())
            continue

        flush_list()
        paragraph_lines.append(line)

    if in_code:
        flush_code()
    flush_paragraph()
    flush_list()

    return "\n".join(blocks)


def markdown_body_length(markdown_text):
    """draft_save の body_length 用に本文テキスト長を算出"""
    text = markdown_text or ""
    # 画像は本文長に含めない
    text = re.sub(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)", "", text)
    # リンクはラベルだけ残す
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1", text)
    # 見出し・リスト記号を除去
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    # 強調・コード記号を除去
    text = text.replace("**", "").replace("*", "").replace("`", "")
    # 改行/空白を除去して文字数を返す
    compact = re.sub(r"\s+", "", text)
    return len(compact)


from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

EMAIL = os.getenv('NOTE_EMAIL')
PASSWORD = os.getenv('NOTE_PASSWORD')

# 使用例
if __name__ == "__main__":
    # 設定
    # EMAIL = ""
    # PASSWORD = ""

    # 記事内容
    TITLE = "朝のコーヒーを少しだけ変えてみた"
    CONTENT = """
# 朝のコーヒーを少し変えてみた話

最近、朝のコーヒーの淹れ方を少しだけ変えてみました。
といっても、豆を変えたわけでも、高級な器具を買ったわけでもありません。

## 単純に、お湯の温度を少し下げてみただけです。

今までは沸騰直後のお湯をそのまま使っていましたが、少しだけ待ってから淹れてみると、味がまろやかになる気がしました。気のせいかもしれません。でも、そう感じられただけでも十分です。

* 朝起きたらまずカーテンを開ける
* コーヒーはゆっくり飲む（急がない）
* 5分だけでも机を片付ける
* スマホを見る前に深呼吸する
* 夜は照明を少し暗くする
* 「まあいっか」を1回は使う

### 朝の時間は、ほんの少しの変化で印象が変わります。

同じ豆、同じカップ、同じ部屋なのに、不思議なものです。

[Google](https://www.google.com)

![random image](https://fastly.picsum.photos/id/223/200/300.jpg?hmac=IZftr2PJy4auHpfBpLuMtFhsxgQYlUgXdV5rFwjGItQ)

こういう小さな実験を、**これから** もたまにやってみようと思います。

![random image 2](https://fastly.picsum.photos/id/361/200/300.jpg?hmac=unS_7uvpA3Q-hJTvI1xNCnlhta-oC6XnWZ4Y11UpjAo)
    """

    # 投稿実行
    post_to_note(EMAIL, PASSWORD, TITLE, CONTENT, None)
