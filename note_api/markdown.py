import re
import uuid
from html import escape


def markdown_to_html(markdown_text):
    """Markdownをnote表示向けHTMLに変換"""
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
            label = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escape(label))
            label = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", label)
            label = re.sub(r"_([^_]+)_", r"<i>\1</i>", label)
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'

        s = re.sub(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)", replace_image, s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", replace_link, s)
        s = re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", s)
        s = re.sub(r"_([^_]+)_", r"<i>\1</i>", s)

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
            items_html = "".join(f"<li>{inline_format(item)}</li>" for item in list_items)
            blocks.append(f"<ul>{items_html}</ul>")
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
        line = raw_line.rstrip()

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

        if not line.strip():
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
    flush_quote()

    return "\n".join(blocks)


def markdown_body_length(markdown_text):
    """draft_save の body_length 用に本文テキスト長を算出"""
    text = markdown_text or ""
    text = re.sub(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1", text)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("*", "").replace("`", "")
    compact = re.sub(r"\s+", "", text)
    return len(compact)
