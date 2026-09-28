"""Publication invariants for a publication researched from public sources.

This checks representation and source structure, not the truth of a legend or
the validity of an image licence. Human editorial/visual review is separate.
"""
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit

MODEL_NOTE = "公開資料をもとに食文化をたどるモデルコースです。編集部の訪問・実食記録ではありません。"


class ReaderText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def output_errors(html):
    parser = ReaderText()
    parser.feed(html)
    text = ' '.join(parser.parts)
    errors = []
    if re.search(r'\bVISITED\b', text, re.I):
        errors.append('訪問記録ではないため、VISITEDという表示は使えません')
    for label in ('お問い合わせ窓口は現在準備中', '世界グルメ100品ツアー（準備中）', '取材資料'):
        if label in text:
            errors.append(f'古い運営・取材表示が残っています：{label}')
    if MODEL_NOTE not in text:
        errors.append('公開資料によるモデルコースという説明がありません')
    return errors


def source_errors(art):
    sources = art.get('sources') or []
    if not sources:
        return ['本文の参照資料がありません（写真クレジットとは別に登録）']
    errors = []
    for i, row in enumerate(sources, 1):
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            errors.append(f'参照資料{i}は資料名とURLの組にしてください')
            continue
        title, url = row
        parsed = urlsplit(url if isinstance(url, str) else '')
        if not isinstance(title, str) or not title.strip() or parsed.scheme not in ('http', 'https') or not parsed.netloc:
            errors.append(f'参照資料{i}の資料名またはURLが不正です')
    return errors
