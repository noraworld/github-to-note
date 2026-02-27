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


def build_args():
    parser = argparse.ArgumentParser(
        description="Post markdown content to note.com draft."
    )
    parser.add_argument("--note-email", default=None)
    parser.add_argument("--note-password", default=None)
    parser.add_argument("--content", default=None)
    parser.add_argument("--content-file", default=None)
    parser.add_argument("--image-path", default=None)
    parser.add_argument("--show-browser", action="store_true")
    return parser.parse_args()


def main():
    load_dotenv()
    args = build_args()

    email = args.note_email or _get_input("note_email", env_fallback="NOTE_EMAIL")
    password = args.note_password or _get_input(
        "note_password", env_fallback="NOTE_PASSWORD"
    )
    content = _read_content(
        args.content or _get_input("content"),
        args.content_file or _get_input("content_file"),
    )
    image_path = args.image_path or _get_input("image_path")
    if args.show_browser:
        os.environ["NOTE_SHOW_BROWSER"] = "1"

    front_matter, body = _split_front_matter_and_body(content)
    title = _extract_title_from_front_matter(front_matter)
    eyecatch_image_url = _extract_front_matter_value(front_matter, "image")
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

    success = post_to_note(
        email,
        password,
        title,
        content,
        image_path,
        eyecatch_image_url=eyecatch_image_url,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
