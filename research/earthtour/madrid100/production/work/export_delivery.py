import hashlib,json,shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
repo=root.parents[1]/'madrid100-github-handoff'
dest=repo/'research/earthtour/madrid100/production'
excluded=[]; copied=[]
for p in root.rglob('*'):
    if not p.is_file(): continue
    rel=p.relative_to(root); s=rel.as_posix()
    if (any(x in rel.parts for x in ['__pycache__','.git','source-cache','originals','thumbs','canary'])
        or s=='qa/draft-before-update.json' or s=='delivery-verification.json'
        or s.startswith('out/review/')
        or (s.startswith('photos/sheets/') and not any(x in p.name for x in ['original-review-','scenes-original-','final-foods-originals']))):
        excluded.append(s); continue
    target=dest/rel; target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,target)
    copied.append({'path':s,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(dest/'export-manifest.json').write_text(json.dumps({'files':copied,'excluded_local_only':excluded},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'exported_files':len(copied),'bytes':sum(x['bytes'] for x in copied),'excluded':len(excluded)},ensure_ascii=False))
ledger=json.loads((root/'photos/rights-wp-ledger.json').read_text(encoding='utf-8'))
print('Ledger entries:',len(ledger))
