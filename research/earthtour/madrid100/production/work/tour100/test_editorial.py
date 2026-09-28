import unittest
from types import SimpleNamespace
from unittest.mock import patch
from . import build
from .editorial import MODEL_NOTE, output_errors, source_errors


class EditorialTests(unittest.TestCase):
    def test_css_visited_is_not_a_visit_claim(self):
        self.assertEqual(output_errors('<style>a:visited {color:red}</style><p>'+MODEL_NOTE+'</p>'), [])

    def test_old_stamp_and_missing_disclosure_are_rejected(self):
        self.assertEqual(len(output_errors('<small>VISITED</small>')), 2)

    def test_legend_is_allowed(self):
        self.assertEqual(output_errors('<p>'+MODEL_NOTE+'</p><p>旅人が伝えたと言われている。</p>'), [])

    def test_photo_credit_cannot_replace_body_sources(self):
        self.assertTrue(source_errors({'photos': {'p1': {'page': 'https://example.org/photo'}}}))
        self.assertTrue(source_errors({'sources': [['資料', 'javascript:alert(1)']]}))
        self.assertEqual(source_errors({'sources': [['資料', 'https://example.org/history']]}), [])

    def test_force_never_writes_failed_manuscript(self):
        with patch.object(build, 'load', return_value={}), patch.object(build, 'selection_errors', return_value=[]), \
             patch.object(build, 'selection_key', return_value='current'), \
             patch.object(build, 'review_state', return_value=('checklist', {'current': True})), \
             patch.object(build, 'report', return_value=1), patch.object(build, 'wp') as wp:
            with self.assertRaisesRegex(SystemExit, '--force'):
                build.cmd_post(SimpleNamespace(folder='unused', force=True))
            wp.assert_not_called()

    def test_force_never_writes_without_visual_review(self):
        with patch.object(build, 'load', return_value={}), patch.object(build, 'selection_errors', return_value=[]), \
             patch.object(build, 'selection_key', return_value='current'), \
             patch.object(build, 'review_state', return_value=('checklist', {'current': True})), \
             patch.object(build, 'report', return_value=0), \
             patch.object(build, 'review_items', return_value=[('写真','new-photo','新しい写真の目視確認')]), \
             patch.object(build, 'wp') as wp:
            with self.assertRaisesRegex(SystemExit, '見直しが終わっていない'):
                build.cmd_post(SimpleNamespace(folder='unused', force=True))
            wp.assert_not_called()


if __name__ == '__main__':
    unittest.main()
