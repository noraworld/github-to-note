import argparse
import os
import re
import sys

from dotenv import load_dotenv

from note_api import post_to_note


def _get_input(name, env_fallback=None, default=None):
    action_key = f"INPUT_{name.upper().replace('-', '_')}"
    value = os.getenv(action_key)
    if value is not None and str(value).strip() != "":
        return value
    if env_fallback:
        env_value = os.getenv(env_fallback)
        if env_value is not None and str(env_value).strip() != "":
            return env_value
    return default


def _is_truthy(value):
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _read_content(content_arg, content_file_arg):
    content = content_arg
    content_file = content_file_arg
    if content_file:
        with open(content_file, "r", encoding="utf-8") as f:
            content = f.read()
    if (not content or str(content).strip() == "") and not sys.stdin.isatty():
        content = sys.stdin.read()
    return content


def _split_front_matter_and_body(content):
    if not content:
        return "", content
    text = content.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return "", content

    end = text.find("\n---\n", 4)
    if end == -1:
        return "", content

    front_matter = text[4:end]
    body = text[end + 5 :]
    return front_matter, body


def _extract_title_from_front_matter(front_matter):
    return _extract_front_matter_value(front_matter, "title")


def _extract_front_matter_value(front_matter, key):
    if not front_matter:
        return None
    for line in front_matter.splitlines():
        m = re.match(rf"^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        value = m.group(1).strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        return value.strip() or None
    return None


def _extract_front_matter_bool(front_matter, key):
    value = _extract_front_matter_value(front_matter, key)
    return _is_truthy(value)


def _strip_quotes(text):
    value = (text or "").strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1].strip()
    return value


def _extract_front_matter_string_list(front_matter, key):
    if not front_matter:
        return []
    lines = front_matter.splitlines()
    key_pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.*)$")
    top_level_key_pattern = re.compile(r"^[A-Za-z0-9_-]+\s*:")

    for idx, line in enumerate(lines):
        m = key_pattern.match(line)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            if not inner:
                return []
            parts = re.findall(r'''(?:'[^']*'|"[^"]*"|[^,]+)''', inner)
            return [_strip_quotes(p) for p in parts if _strip_quotes(p)]
        if rest:
            value = _strip_quotes(rest)
            return [value] if value else []

        items = []
        for sub in lines[idx + 1 :]:
            if not sub.strip():
                continue
            if top_level_key_pattern.match(sub.strip()):
                break
            item_match = re.match(r"^\s*-\s*(.+?)\s*$", sub)
            if item_match:
                value = _strip_quotes(item_match.group(1))
                if value:
                    items.append(value)
            elif items:
                break
        return items
    return []


def _upsert_note_id_to_content_file(content_file, note_id):
    try:
        with open(content_file, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as exc:
        print(f"note_id の書き戻し失敗: ファイル読み込み不可 ({exc})")
        return False

    front_matter, body = _split_front_matter_and_body(source)
    if not front_matter:
        print("note_id の書き戻しスキップ: YAML front matter がありません。")
        return False

    note_id_line = f"note_id: {note_id}"
    if re.search(r"^\s*note_id\s*:\s*.+$", front_matter, flags=re.MULTILINE):
        updated_front_matter = re.sub(
            r"^\s*note_id\s*:\s*.+$",
            note_id_line,
            front_matter,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        if front_matter.endswith("\n"):
            updated_front_matter = f"{front_matter}{note_id_line}"
        else:
            updated_front_matter = f"{front_matter}\n{note_id_line}"

    updated_source = f"---\n{updated_front_matter}\n---\n{body}"
    try:
        with open(content_file, "w", encoding="utf-8") as f:
            f.write(updated_source)
    except Exception as exc:
        print(f"note_id の書き戻し失敗: ファイル書き込み不可 ({exc})")
        return False

    print(f"content_file に note_id を書き戻しました: {content_file} (note_id={note_id})")
    return True


def build_args():
    parser = argparse.ArgumentParser(
        description="Post markdown content to note.com draft."
    )
    parser.add_argument("--note-email", default=None)
    parser.add_argument("--note-password", default=None)
    parser.add_argument("--content", default=None)
    parser.add_argument("--content-file", default=None)
    parser.add_argument("--image-path", default=None)
    parser.add_argument("--article-id", default=None)
    parser.add_argument("--write-note-id", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--show-browser", action="store_true")
    return parser.parse_args()


def main():
    load_dotenv()
    args = build_args()

    email = args.note_email or _get_input("note_email", env_fallback="NOTE_EMAIL")
    password = args.note_password or _get_input(
        "note_password", env_fallback="NOTE_PASSWORD"
    )
    content_arg = args.content or _get_input("content")
    content_file = args.content_file or _get_input("content_file")
    content = _read_content(content_arg, content_file)
    image_path = args.image_path or _get_input("image_path")
    article_id = args.article_id or _get_input("article_id")
    write_note_id = args.write_note_id or _is_truthy(_get_input("write_note_id"))
    publish_input = _is_truthy(_get_input("publish"))
    if args.show_browser:
        os.environ["NOTE_SHOW_BROWSER"] = "1"

    front_matter, body = _split_front_matter_and_body(content)
    title = _extract_title_from_front_matter(front_matter)
    eyecatch_image_url = _extract_front_matter_value(front_matter, "image")
    front_matter_note_id = _extract_front_matter_value(front_matter, "note_id")
    front_matter_published = _extract_front_matter_bool(front_matter, "published")
    hashtags = []
    for tag in _extract_front_matter_string_list(front_matter, "tags"):
        value = str(tag).strip()
        if not value:
            continue
        if not value.startswith("#"):
            value = f"#{value}"
        hashtags.append(value)
    hashtags = list(dict.fromkeys(hashtags))
    publish = args.publish or publish_input or front_matter_published
    article_id = article_id or front_matter_note_id
    content = body

    if not email:
        print("Missing note email. Set --note-email or NOTE_EMAIL.")
        return 1
    if not password:
        print("Missing note password. Set --note-password or NOTE_PASSWORD.")
        return 1
    if not title:
        print("Missing title in YAML front matter (title: ...).")
        return 1
    if not content:
        print("Missing content. Set --content / --content-file / INPUT_CONTENT.")
        return 1

    success, posted_article_id, created_new = post_to_note(
        email,
        password,
        title,
        content,
        image_path,
        eyecatch_image_url=eyecatch_image_url,
        article_id=article_id,
        publish=publish,
        hashtags=hashtags,
    )
    if success and write_note_id:
        if created_new and posted_article_id:
            if content_file:
                _upsert_note_id_to_content_file(content_file, posted_article_id)
            else:
                print("note_id の書き戻しスキップ: content_file が指定されていません。")
        else:
            print("note_id の書き戻しスキップ: 新規投稿ではないため実施しません。")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
