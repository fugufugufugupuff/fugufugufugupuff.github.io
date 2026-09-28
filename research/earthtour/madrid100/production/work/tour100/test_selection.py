import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch

if __package__:
    from . import build
    from .selection import selection_errors, selection_key
else:
    import build
    from selection import selection_errors, selection_key


def manuscript():
    # Synthetic evidence exercises the schema, not a real editorial approval.
    return {"stops": [{"dishes": [
        {"name": f"dish{i}", "selection": {
            "kind": "city" if i < 10 else "national" if i < 80 else "embedded",
            "reason": "test relation", "distinct": "test independent dish",
            "evidence": "test evidence", "sources": ["https://example.org/history"]}}
        for i in range(100)]}]}


class SelectionTests(unittest.TestCase):
    def test_valid_distribution(self):
        self.assertEqual(selection_errors(manuscript()), [])

    def test_legacy_article_fails(self):
        art = manuscript()
        for d in art["stops"][0]["dishes"]:
            del d["selection"]
        self.assertEqual(sum("selection（" in e for e in selection_errors(art)), 100)

    def test_generic_and_missing_evidence_fail(self):
        art = manuscript()
        item = art["stops"][0]["dishes"][0]["selection"]
        item.update(kind="generic", evidence=" ", sources=["not-a-url"])
        errs = selection_errors(art)
        for fragment in ("採用不可", "evidence", "URL"):
            self.assertTrue(any(fragment in e for e in errs))

    def test_embedded_overflow_fails(self):
        art = manuscript()
        art["stops"][0]["dishes"][79]["selection"]["kind"] = "embedded"
        errs = selection_errors(art)
        self.assertTrue(any("80品" in e for e in errs))
        self.assertTrue(any("20品" in e for e in errs))

    def test_city_floor_fails(self):
        art = manuscript()
        art["stops"][0]["dishes"][0]["selection"]["kind"] = "national"
        self.assertTrue(any("10品" in e for e in selection_errors(art)))

    def test_edit_invalidates_signoff_not_media_cache(self):
        art = manuscript()
        key = selection_key(art)
        art["_media"] = {"cache": "new"}
        self.assertEqual(selection_key(art), key)
        art["stops"][0]["dishes"][0]["name"] = "replacement"
        self.assertNotEqual(selection_key(art), key)

    def test_force_cannot_post_missing_selection(self):
        art = {"stops": [{"dishes": [{"name": "キムチ"}]}]}
        with patch.object(build, "load", return_value=art), patch.object(build, "wp") as wp:
            with self.assertRaisesRegex(SystemExit, "選定が未合格"):
                build.cmd_post(SimpleNamespace(folder="unused", force=True))
            wp.assert_not_called()

    def test_force_cannot_post_stale_review(self):
        art = manuscript()
        old_key = selection_key(art)
        art["stops"][0]["dishes"][0]["gloss"] = "changed"
        with patch.object(build, "load", return_value=art), patch.object(build, "wp") as wp, \
                patch.object(build, "review_state", return_value=("checklist", {old_key: True})):
            with self.assertRaisesRegex(SystemExit, "選定レビューが未完了"):
                build.cmd_post(SimpleNamespace(folder="unused", force=True))
            wp.assert_not_called()


    def test_replacement_does_not_inherit_dish_or_stop_checks(self):
        art = manuscript()
        art["meta"] = {"month": "test"}
        art["stops"][0].update(id="s01", day=1, time="12:00", place_name="old place")
        for d in art["stops"][0]["dishes"]:
            d["price"] = {"seal": "test price"}
        old_keys = {k for _, k, _ in build.review_items(art)}
        self.assertEqual(old_keys, {k for _, k, _ in build.review_items(art)})
        art["stops"][0]["dishes"][0]["name"] = "replacement"
        art["stops"][0]["place_name"] = "new place"
        self.assertFalse(old_keys & {k for _, k, _ in build.review_items(art)})


if __name__ == "__main__":
    unittest.main()
