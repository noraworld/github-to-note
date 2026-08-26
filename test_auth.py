import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


auth_module_path = Path(__file__).resolve().parent / "note_api" / "auth.py"
auth_spec = spec_from_file_location("auth_module", auth_module_path)
auth_module = module_from_spec(auth_spec)
try:
    auth_spec.loader.exec_module(auth_module)
except ModuleNotFoundError as exc:
    if exc.name != "selenium":
        raise
    auth_module = None
else:
    _find_first = auth_module._find_first
    _is_editable_text_field = auth_module._is_editable_text_field


class FakeElement:
    def __init__(
        self,
        *,
        displayed=True,
        enabled=True,
        tag_name="input",
        attrs=None,
    ):
        self._displayed = displayed
        self._enabled = enabled
        self.tag_name = tag_name
        self._attrs = attrs or {}

    def is_displayed(self):
        return self._displayed

    def is_enabled(self):
        return self._enabled

    def get_attribute(self, name):
        return self._attrs.get(name)


class FakeDriver:
    def __init__(self, elements_by_selector):
        self.elements_by_selector = elements_by_selector

    def find_elements(self, by, value):
        return self.elements_by_selector.get((by, value), [])


@unittest.skipIf(auth_module is None, "selenium is not installed")
class AuthElementSelectionTest(unittest.TestCase):
    def test_editable_text_field_rejects_hidden_and_readonly_inputs(self):
        self.assertFalse(_is_editable_text_field(FakeElement(displayed=False)))
        self.assertFalse(
            _is_editable_text_field(FakeElement(attrs={"readonly": "true"}))
        )
        self.assertFalse(_is_editable_text_field(FakeElement(attrs={"type": "hidden"})))
        self.assertTrue(_is_editable_text_field(FakeElement(attrs={"type": "email"})))

    def test_find_first_returns_first_editable_match(self):
        hidden = FakeElement(displayed=False, attrs={"type": "email"})
        editable = FakeElement(attrs={"type": "email"})
        driver = FakeDriver({("css selector", "input"): [hidden, editable]})

        self.assertIs(
            _find_first(
                driver,
                [("css selector", "input")],
                _is_editable_text_field,
            ),
            editable,
        )


if __name__ == "__main__":
    unittest.main()
