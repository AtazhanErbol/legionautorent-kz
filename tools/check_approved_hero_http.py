"""Read-only HTTP checks for the approved film referenced by the home page."""
import argparse
import json
import os
import struct
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class HeroParser(HTMLParser):
    video = ''

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if 'data-mercedes-preview' in attributes:
            self.video = attributes.get('data-video', '')


def check(base):
    with urlopen(base.rstrip('/') + '/', timeout=20) as response:
        page = HeroParser()
        page.feed(response.read().decode('utf-8'))
    url = urljoin(base, page.video)
    parts = urlsplit(url)
    if not page.video or parts.netloc != urlsplit(base).netloc or not parts.path.startswith('/static/hero/'):
        raise ValueError('The home page must reference the approved local hero film.')
    relative = parts.path.removeprefix('/static/')
    if '..' in Path(relative).parts:
        raise ValueError('Unsafe asset path.')
    data = (ROOT / 'staticfiles' / relative).read_bytes()
    boxes, offset = [], 0
    while offset + 8 <= len(data):
        size, kind = struct.unpack('>I4s', data[offset:offset + 8])
        if size == 1:
            size = struct.unpack('>Q', data[offset + 8:offset + 16])[0]
        if not size:
            size = len(data) - offset
        if size < 8 or offset + size > len(data):
            raise ValueError('Invalid MP4 box.')
        boxes.append(kind.decode('ascii'))
        offset += size
    checks = {'faststart_moov_before_mdat': boxes.index('moov') < boxes.index('mdat')}
    with urlopen(Request(url, method='HEAD'), timeout=20) as response:
        checks.update({
            'head_status_200': response.status == 200,
            'video_mime': response.headers.get_content_type() == 'video/mp4',
            'head_length': int(response.headers.get('Content-Length', 0)) == len(data),
            'immutable_cache': 'immutable' in response.headers.get('Cache-Control', ''),
            'accept_ranges': response.headers.get('Accept-Ranges') == 'bytes',
        })
    for label, header, start, end in [
        ('start', 'bytes=0-1023', 0, 1023),
        ('middle', 'bytes=2048-4095', 2048, 4095),
        ('tail', 'bytes=-1024', len(data) - 1024, len(data) - 1),
    ]:
        with urlopen(Request(url, headers={'Range': header, 'Accept-Encoding': 'br, gzip'}), timeout=20) as response:
            checks.update({
                f'{label}_206': response.status == 206,
                f'{label}_range': response.headers.get('Content-Range') == f'bytes {start}-{end}/{len(data)}',
                f'{label}_bytes': response.read() == data[start:end + 1],
                f'{label}_uncompressed': not response.headers.get('Content-Encoding'),
            })
    try:
        with urlopen(Request(url, headers={'Range': f'bytes={len(data)}-'}), timeout=20):
            checks['out_of_bounds_416'] = False
    except HTTPError as response:
        checks['out_of_bounds_416'] = response.code == 416
        response.close()
    return {'url': url, 'video_bytes': len(data), 'mp4_boxes': boxes,
            'checks': checks, 'passed': all(checks.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=os.getenv('PREVIEW_URL', 'http://127.0.0.1:8004'))
    args = parser.parse_args()
    report = check(args.base_url)
    (ROOT / 'reports/approved_hero_http.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
    raise SystemExit(0 if report['passed'] else 1)
