import os
import sys

from note_api import post_to_note


def get_input(name, required=False, default=None):
    key = f"INPUT_{name.upper().replace('-', '_')}"
    value = os.getenv(key, default)
    if required and (value is None or str(value).strip() == ""):
        print(f"Missing required input: {name}")
        sys.exit(1)
    return value


def main():
    email = get_input("note_email", required=True)
    password = get_input("note_password", required=True)
    title = get_input("title", required=True)

    content = get_input("content", required=False)
    content_file = get_input("content_file", required=False)
    if content_file:
        try:
            with open(content_file, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            print(f"Failed to read content_file: {content_file} ({exc})")
            sys.exit(1)

    if not content:
        print("Either 'content' or 'content_file' must be provided")
        sys.exit(1)

    image_path = get_input("image_path", required=False)

    success = post_to_note(email, password, title, content, image_path)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
