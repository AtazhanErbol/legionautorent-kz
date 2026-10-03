"""Read-only check of the deployed MP4 MIME, byte ranges and faststart layout."""
import json, os, struct
from pathlib import Path
from urllib.request import Request, urlopen

root=Path(__file__).resolve().parents[1]
asset=root/'static/video/hero-drive.mp4'
data=asset.read_bytes()
boxes=[]; offset=0
while offset+8<=len(data):
    size,kind=struct.unpack('>I4s',data[offset:offset+8])
    if size==1:size=struct.unpack('>Q',data[offset+8:offset+16])[0]
    if not size:size=len(data)-offset
    if size<8:raise ValueError('Invalid MP4 box')
    boxes.append(kind.decode('ascii'));offset+=size
url=os.getenv('PREVIEW_URL','http://127.0.0.1:8004')+'/static/video/hero-drive.mp4'
with urlopen(Request(url,headers={'Range':'bytes=0-1023'}),timeout=20) as response:
    checks={
        'range_status_206':response.status==206,
        'video_mime':response.headers.get_content_type()=='video/mp4',
        'content_range':response.headers.get('Content-Range')==f'bytes 0-1023/{len(data)}',
        'range_bytes_match':response.read()==data[:1024],
        'faststart_moov_before_mdat':boxes.index('moov')<boxes.index('mdat'),
    }
report={'url':url,'video_bytes':len(data),'mp4_boxes':boxes,'checks':checks,'passed':all(checks.values())}
(root/'reports/hero_story_http.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
assert report['passed'],report
