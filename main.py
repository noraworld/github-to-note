import argparse
import os
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


def build_args():
    parser = argparse.ArgumentParser(
        description="Post markdown content to note.com draft."
    )
    parser.add_argument("--note-email", default=None)
    parser.add_argument("--note-password", default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--content", default=None)
    parser.add_argument("--content-file", default=None)
    parser.add_argument("--image-path", default=None)
    return parser.parse_args()


def main():
    load_dotenv()
    args = build_args()

    email = args.note_email or _get_input("note_email", env_fallback="NOTE_EMAIL")
    password = args.note_password or _get_input(
        "note_password", env_fallback="NOTE_PASSWORD"
    )
    title = args.title or _get_input("title", env_fallback="NOTE_TITLE")
    content = _read_content(
        args.content or _get_input("content"),
        args.content_file or _get_input("content_file"),
    )
    image_path = args.image_path or _get_input("image_path")

    if not email:
        print("Missing note email. Set --note-email or NOTE_EMAIL.")
        return 1
    if not password:
        print("Missing note password. Set --note-password or NOTE_PASSWORD.")
        return 1
    if not title:
        print("Missing title. Set --title or INPUT_TITLE.")
        return 1
    if not content:
        print("Missing content. Set --content / --content-file / INPUT_CONTENT.")
        return 1

    success = post_to_note(email, password, title, content, image_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
