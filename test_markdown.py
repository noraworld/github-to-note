import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


markdown_module_path = Path(__file__).resolve().parent / "note_api" / "markdown.py"
markdown_spec = spec_from_file_location("markdown_module", markdown_module_path)
markdown_module = module_from_spec(markdown_spec)
markdown_spec.loader.exec_module(markdown_module)

markdown_body_length = markdown_module.markdown_body_length
markdown_to_html = markdown_module.markdown_to_html
sanitize_markdown = markdown_module.sanitize_markdown


class SanitizeMarkdownTest(unittest.TestCase):
    def test_removes_multiline_html_comments_outside_code_fences(self):
        markdown = "\n".join(
            [
                "before",
                "<!--",
                "hidden line 1",
                "hidden line 2",
                "-->",
                "after",
            ]
        )

        sanitized = sanitize_markdown(markdown)

        self.assertNotIn("hidden line 1", sanitized)
        self.assertNotIn("hidden line 2", sanitized)
        self.assertIn("before", sanitized)
        self.assertIn("after", sanitized)

    def test_removes_inline_and_multiline_html_comments_on_same_pass(self):
        markdown = "\n".join(
            [
                "before <!-- hidden --> after",
                "keep <!-- hidden",
                "still hidden --> visible",
            ]
        )

        self.assertEqual(
            sanitize_markdown(markdown),
            "\n".join(["before  after", "keep ", " visible"]),
        )

    def test_keeps_html_comments_inside_code_fences(self):
        markdown = "\n".join(
            [
                "```",
                "<!--",
                "visible in code",
                "-->",
                "```",
            ]
        )

        self.assertEqual(sanitize_markdown(markdown), markdown)

    def test_does_not_toggle_code_fence_inside_html_comment(self):
        markdown = "\n".join(
            [
                "before",
                "<!--",
                "```",
                "hidden",
                "```",
                "-->",
                "after",
            ]
        )

        self.assertNotIn("hidden", sanitize_markdown(markdown))
        self.assertNotIn("```", sanitize_markdown(markdown))

    def test_rendered_html_and_body_length_do_not_include_comments(self):
        markdown = "\n".join(
            [
                "visible",
                "<!--",
                "hidden",
                "-->",
            ]
        )

        self.assertNotIn("hidden", markdown_to_html(markdown))
        self.assertEqual(markdown_body_length(markdown), len("visible"))


if __name__ == "__main__":
    unittest.main()
