"""Editorial selection gate. Metadata cannot replace reading its cited sources."""
import hashlib
import json
from urllib.parse import urlparse

KINDS = {"city", "regional", "national", "embedded"}


def selection_key(art):
    # Any manuscript change invalidates the previous editorial sign-off.
    content = {k: v for k, v in art.items() if not k.startswith("_")}
    raw = json.dumps(content, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "selection-v1-" + hashlib.sha256(raw).hexdigest()[:20]


def selection_errors(art):
    errors, counts = [], dict.fromkeys(KINDS, 0)
    dishes = [d for s in art.get("stops", []) for d in s.get("dishes", [])]
    for i, dish in enumerate(dishes, 1):
        label = f"選定 {i:03d} {dish.get('name', '')}"
        item = dish.get("selection")
        if not isinstance(item, dict):
            errors.append(f"{label}：selection（土地との関係・根拠）がない")
            continue
        kind = item.get("kind")
        if kind not in KINDS:
            errors.append(f"{label}：city/regional/national/embedded以外は採用不可")
        else:
            counts[kind] += 1
        for field in ("reason", "distinct", "evidence"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}：selection.{field} がない")
        sources = item.get("sources")
        if (not isinstance(sources, list) or not sources
                or any(not isinstance(u, str) or urlparse(u).scheme not in {"https", "http"}
                       or not urlparse(u).netloc for u in sources)):
            errors.append(f"{label}：関係を裏付ける個別ページのURLが必要")
    if len(dishes) == 100:
        if sum(counts[k] for k in ("city", "regional", "national")) < 80:
            errors.append("選定：都市・周辺地域・対象国の料理を合計80品以上にする")
        if counts["city"] < 10:
            errors.append("選定：対象都市との具体的な関係があるcityを10品以上にする")
        if counts["embedded"] > 20:
            errors.append("選定：都市に定着した国外由来の料理embeddedは20品以下")
    return errors
