"""Offline QA must preserve source-page links that look like image URLs."""
import tempfile
import unittest
from unittest.mock import patch

if __package__:
    from . import build
else:
    import build


class LocalizeTests(unittest.TestCase):
    def test_source_page_is_not_downloaded_as_an_image(self):
        image = 'https://example.org/food.jpg'
        credit = 'https://commons.wikimedia.org/wiki/File:Food.jpg'
        css = 'https://example.org/style.css'
        html = f'<link rel="stylesheet" href="{css}"><img src="{image}"><a href="{credit}">Credit</a>'
        with tempfile.TemporaryDirectory() as folder, patch.object(build, '_fetch', return_value=b'asset') as fetch:
            result, failures = build.localize(html, folder)
        self.assertEqual(failures, 0)
        self.assertEqual({call.args[0] for call in fetch.call_args_list}, {image, css})
        self.assertIn(f'href="{credit}"', result)
        self.assertNotIn(f'src="{image}"', result)


if __name__ == '__main__':
    unittest.main()
