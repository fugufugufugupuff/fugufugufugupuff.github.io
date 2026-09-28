"""Save this user-requested working draft without claiming production-gate approval.
The canonical post command remains unchanged and blocked by missing dish photos.
Never publishes, schedules, or updates an existing public post.
"""
import json,sys,hashlib,re
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'work/tour100'))
import build
a=build.load(str(R));body=(R/'out/post.html').read_text(encoding='utf-8')
assert len([d for s in a['stops'] for d in s['dishes']])==100
assert '<!--wge-css:t100-->' in body
assert not build.output_errors(body)
existing=build.wp('wp/v2/posts?context=edit&status=publish,draft,pending,future,private&per_page=100&slug='+a['meta']['slug'])
pid_file=R/'post_id.txt';pid=int(pid_file.read_text()) if pid_file.exists() else None
if existing and not pid:raise RuntimeError('Existing matching post discovered; inspect before writing')
if pid:
 old=build.wp(f'wp/v2/posts/{pid}?context=edit')
 assert old['status']=='draft' and old['slug']==a['meta']['slug']
 (R/'qa/draft-before-update.json').write_text(json.dumps({k:old[k] for k in ['id','status','slug','title','content','featured_media']},ensure_ascii=False,indent=1),encoding='utf-8')
cover=a['photos'][a['cover']['photos'][0]];fid=a['_media'][cover['url']]['id']
payload=dict(title=a['meta']['title'],content=body,slug=a['meta']['slug'],excerpt=a['meta']['excerpt'],categories=[73],featured_media=fid,status='draft')
result=build.wp('wp/v2/posts'+('/'+str(pid) if pid else ''),payload)
pid=result['id'];pid_file.write_text(str(pid),encoding='utf-8')
saved=build.wp(f'wp/v2/posts/{pid}?context=edit')
actual=saved['content']['raw'];sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
check=dict(site='https://earthtour.jp',id=pid,status=saved['status'],slug=saved['slug'],featured_media=saved['featured_media'],expected_featured_media=fid,body_equal=actual==body,body_sha256=sha(actual),expected_sha256=sha(body),dish_anchors=len(re.findall(r'id="dish-\d{3}"',actual)),image_urls=len(set(re.findall(r'<img[^>]+src="([^"]+)"',actual))),categories=saved['categories'],production_gate_passed=False,reason='13 dish photographs unavailable; M003 partial; draft retained as explicitly requested working artifact')
(R/'qa/wp-readback.json').write_text(json.dumps(check,ensure_ascii=False,indent=1),encoding='utf-8')
(R/'qa/wp-saved-body.html').write_text(actual,encoding='utf-8')
assert check['status']=='draft' and check['body_equal'] and saved['featured_media']==fid and check['dish_anchors']==100
print(json.dumps(check,ensure_ascii=False))
