import re
import uuid
from html import escape


IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)")
LINK_PATTERN = re.compile(r"\[((?:[^\[\]]|\[[^\[\]]*\])+)\]\((https?://[^)\s]+)\)")
ASCII_BLANK_PATTERN = re.compile(r"^[ \t]*$")


def is_markdown_blank_line(line):
    return ASCII_BLANK_PATTERN.fullmatch(line) is not None


def sanitize_markdown(markdown_text):
    """本文用 Markdown を正規化する。HTML コメントはコードフェンス外のみ除去する。"""
    text = (markdown_text or "").replace("\r\n", "\n")
    if not text:
        return ""

    sanitized_lines = []
    in_code = False
    code_fence_pattern = re.compile(r"^\s*(```|~~~)")
    comment_pattern = re.compile(r"<!--.*?-->", flags=re.DOTALL)

    for raw_line in text.split("\n"):
        if code_fence_pattern.match(raw_line):
            in_code = not in_code
            sanitized_lines.append(raw_line)
            continue

        if in_code:
            sanitized_lines.append(raw_line)
            continue

        cleaned_line = comment_pattern.sub("", raw_line)
        sanitized_lines.append(cleaned_line)

    return "\n".join(sanitized_lines)


def markdown_to_html(markdown_text):
    """Markdownをnote表示向けHTMLに変換"""
    text = sanitize_markdown(markdown_text).strip("\n")
    if not text:
        return ""

    def block_id():
        return str(uuid.uuid4())

    def inline_format(s):
        # note does not support inline code spans; keep them as plain text.
        s = re.sub(r"`([^`]+)`", r"\1", s)
        placeholders = []

        def replace_image(match):
            alt = escape(match.group(1).strip())
            url = escape(match.group(2).strip(), quote=True)
            placeholders.append(
                f'<img src="{url}" alt="{alt}" loading="lazy" class="is-slide" data-modal="true">'
            )
            return f"@@PLACEHOLDER_{len(placeholders) - 1}@@"

        def replace_link(match):
            label = match.group(1).strip()
            url = escape(match.group(2).strip(), quote=True)
            label = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escape(label))
            label = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", label)
            placeholders.append(
                f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'
            )
            return f"@@PLACEHOLDER_{len(placeholders) - 1}@@"

        def replace_bare_url(match):
            url = match.group(0)
            trailing = ""
            while url and url[-1] in ".,!?;:":
                trailing = url[-1] + trailing
                url = url[:-1]
            placeholders.append(
                f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(url)}</a>'
            )
            return f"@@PLACEHOLDER_{len(placeholders) - 1}@@" + trailing

        s = IMAGE_PATTERN.sub(replace_image, s)
        s = LINK_PATTERN.sub(replace_link, s)
        s = escape(s)
        s = re.sub(r"https?://[^\s<]+", replace_bare_url, s)
        s = re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        for idx, html in enumerate(placeholders):
            s = s.replace(f"@@PLACEHOLDER_{idx}@@", html)

        return s

    def image_block(line):
        m = IMAGE_PATTERN.fullmatch(line.strip())
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
    quote_lines = []
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
            parts = []
            current_depth = 0
            list_stack = []

            for depth, list_type, item in list_items:
                # note supports up to 5 nested levels for lists.
                target_depth = max(1, min(depth, 5))
                if target_depth > current_depth + 1:
                    target_depth = current_depth + 1

                while current_depth > target_depth:
                    parts.append(f"</li></{list_stack.pop()}>")
                    current_depth -= 1

                if current_depth == target_depth and current_depth > 0:
                    if list_stack[-1] == list_type:
                        parts.append("</li>")
                    else:
                        parts.append(f"</li></{list_stack.pop()}>")
                        current_depth -= 1

                while current_depth < target_depth:
                    open_tag = list_type if current_depth + 1 == target_depth else "ul"
                    parts.append(f"<{open_tag}>")
                    list_stack.append(open_tag)
                    current_depth += 1

                bid = block_id()
                parts.append(
                    f'<li><p name="{bid}" id="{bid}">{inline_format(item)}</p>'
                )

            while current_depth > 0:
                parts.append(f"</li></{list_stack.pop()}>")
                current_depth -= 1

            blocks.append("".join(parts))
            list_items.clear()

    def flush_quote():
        if quote_lines:
            quote = "<br>".join(inline_format(line) for line in quote_lines)
            bid = block_id()
            blocks.append(
                f'<blockquote><p name="{bid}" id="{bid}">{quote}</p></blockquote>'
            )
            quote_lines.clear()

    def flush_code():
        if code_lines:
            code = "\n".join(escape(line) for line in code_lines)
            blocks.append(f"<pre><code>{code}</code></pre>")
            code_lines.clear()

    for raw_line in lines:
        line = raw_line.rstrip("\r")

        if line.strip().startswith("```"):
            flush_paragraph()
            flush_list()
            flush_quote()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if is_markdown_blank_line(line):
            flush_paragraph()
            flush_list()
            flush_quote()
            continue

        img_block = image_block(line)
        if img_block is not None:
            flush_paragraph()
            flush_list()
            flush_quote()
            blocks.append(img_block)
            continue

        if re.match(r"^\s*---\s*$", line):
            flush_paragraph()
            flush_list()
            flush_quote()
            blocks.append("<hr>")
            continue

        quote_match = re.match(r"^>\s?(.*)$", line)
        if quote_match:
            flush_paragraph()
            flush_list()
            quote_lines.append(quote_match.group(1))
            continue
        flush_quote()

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            flush_paragraph()
            flush_list()
            hash_count = len(heading_match.group(1))
            if hash_count <= 2:
                level = 2
            else:
                level = 3
            content = inline_format(heading_match.group(2).strip())
            bid = block_id()
            blocks.append(f'<h{level} name="{bid}" id="{bid}">{content}</h{level}>')
            continue

        bullet_match = re.match(r"^(\s*)[-*]\s+(.+)$", line)
        if bullet_match:
            flush_paragraph()
            indent_width = len(bullet_match.group(1).expandtabs(4))
            depth = (indent_width // 2) + 1
            list_items.append((depth, "ul", bullet_match.group(2).strip()))
            continue

        numbered_match = re.match(r"^(\s*)\d+[.)]\s+(.+)$", line)
        if numbered_match:
            flush_paragraph()
            indent_width = len(numbered_match.group(1).expandtabs(4))
            depth = (indent_width // 2) + 1
            list_items.append((depth, "ol", numbered_match.group(2).strip()))
            continue

        flush_list()
        paragraph_lines.append(line)

    if in_code:
        flush_code()
    flush_paragraph()
    flush_list()
    flush_quote()

    return "\n".join(blocks)


def markdown_body_length(markdown_text):
    """draft_save の body_length 用に本文テキスト長を算出"""
    text = sanitize_markdown(markdown_text)
    text = IMAGE_PATTERN.sub("", text)
    text = LINK_PATTERN.sub(r"\1", text)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("*", "").replace("`", "")
    compact = re.sub(r"[ \t\r\n]+", "", text)
    return len(compact)
