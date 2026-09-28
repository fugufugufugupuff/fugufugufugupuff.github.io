"""Photo association must not confuse similarly named foods."""
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
if __package__:
    from . import photos
else:
    import photos


class PhotoAssociationTests(unittest.TestCase):
    def test_similar_names_require_exact_match(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'photos').mkdir()
            art = {'cover': {'tag_dish': 3}, 'stops': [{'day': 1, 'time': '09:00', 'dishes': [
                {'name': 'バター'}, {'name': 'バターミルク'},
                {'name': '別名', 'aka': '発酵バター'}]}]}
            rows = [dict(id=k, role='dish', dish=n, url='https://example.org/'+k,
                         license='by', creator='Tester') for k, n in [
                         ('buttermilk', 'バターミルク'), ('cultured', '発酵バター')]]
            photos.save(folder, art)
            photos.jsave(str(root / 'photos' / 'part_test.json'), rows)
            photos.attach(folder)
            dishes = photos.load(folder)['stops'][0]['dishes']
            self.assertIsNone(dishes[0]['photo'])
            self.assertEqual(dishes[1]['photo'], 'buttermilk')
            self.assertEqual(dishes[2]['photo'], 'cultured')
            self.assertEqual(photos.load(folder)['cover']['photos'][0], 'cultured')

    def test_existing_source_is_reused_without_another_import(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = 'https://example.org/photo.jpg'
            uploaded = 'https://earthtour.jp/wp-content/uploads/photo.jpg'
            art = {'meta': {'slug': 'test-100-dishes-tour'}, 'stops': [],
                   'cover': {'photos': ['hero']}, 'photos': {
                       'scene': {'orig_url': source, 'url': uploaded},
                       'hero': {'url': source}}}
            (root / 'article.json').write_text(json.dumps(art), encoding='utf-8')
            with patch.object(photos, 'api', return_value={'ok': True, 'version': 'test'}) as api:
                photos.do_import(folder)
            api.assert_called_once_with('health')
            result = json.loads((root / 'article.json').read_text(encoding='utf-8'))
            self.assertEqual(result['photos']['hero'], {'orig_url': source, 'url': uploaded})


if __name__ == '__main__':
    unittest.main()
