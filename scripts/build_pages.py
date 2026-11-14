#!/usr/bin/env python3
"""Build the parallel Pages site from a pinned, already-public release."""
from pathlib import Path, PurePosixPath
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
from urllib.parse import quote
import argparse, hashlib, json, re, time

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://levent.top'
PUBLIC_ROOT = ORIGIN + '/showcase/'
TEXT_TYPES = {'.html', '.css', '.js', '.svg', '.json', '.md'}
SECRET = re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}|LTAI[0-9a-zA-Z]{16,}|gh[pousr]_[A-Za-z0-9]{30,}')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def redirect_page(destination, title):
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><meta http-equiv="refresh" content="0;url={destination}">'
            '<script>location.replace(' + json.dumps(destination) + ')</script>'
            f'<p><a href="{destination}">{title}</a></p></html>')


def build(output, cache):
    manifest = json.loads((ROOT / 'source-manifest.json').read_text())
    paths = [name for name in manifest if not name.startswith('studio/')]
    for name in paths:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError('Invalid source path: ' + name)
    if output.exists():
        raise RuntimeError('Output already exists; choose a new output directory: ' + str(output))
    output.mkdir(parents=True)
    cache.mkdir(parents=True, exist_ok=True)

    def retrieve(name):
        expected = manifest[name]
        cached = cache / expected
        if cached.is_file() and digest(cached.read_bytes()) == expected:
            return name, cached.read_bytes()
        for attempt in range(3):
            try:
                request = Request(PUBLIC_ROOT + quote(name, safe='/'), headers={
                    'Accept-Encoding': 'identity', 'Cache-Control': 'no-cache',
                    'User-Agent': 'Levent-Pages-release/1.0'})
                with urlopen(request, timeout=30) as response:
                    data = response.read()
                if digest(data) != expected:
                    raise ValueError('The live release changed; refresh the pinned manifest: ' + name)
                cached.write_bytes(data)
                return name, data
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)

    changes = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for name, data in pool.map(retrieve, paths):
            target = output / 'showcase' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.suffix in TEXT_TYPES:
                text = data.decode('utf-8')
                if SECRET.search(text):
                    raise ValueError('Credential pattern in public source: ' + name)
                before = text
                text = text.replace('/api/showcase/content', '/showcase/data/showcase-content.json')
                text = text.replace('"/showcase/studio/"', '"https://levent.top/showcase/studio/"')
                for endpoint in ['/admin/', '/h5/']:
                    for delimiter in ['"', "'"]:
                        text = text.replace(delimiter + endpoint + delimiter,
                                            delimiter + ORIGIN + endpoint + delimiter)
                if name in ['projects/viewer/index.html', 'projects/reader/index.html']:
                    guard = ('<script>(()=>{const id=new URLSearchParams(location.search).get("id")||"eventos";'
                             'if(id==="eventos")location.replace(' + json.dumps(PUBLIC_ROOT + name) +
                             '+location.search+location.hash);})();</script>')
                    text = text.replace('<head>', '<head>' + guard, 1)
                if text != before:
                    changes.append(name)
                data = text.encode('utf-8')
            target.write_bytes(data)

    snapshot = json.loads((ROOT / 'content-snapshot.json').read_text())
    snapshot = {key: snapshot.get(key, {} if key != 'projects' else [])
                for key in ['homepage', 'overrides', 'projects']}
    text = json.dumps(snapshot, ensure_ascii=False)
    if SECRET.search(text):
        raise ValueError('Credential pattern in content snapshot')
    (output / 'showcase/data').mkdir(exist_ok=True)
    (output / 'showcase/data/showcase-content.json').write_text(text + '\n')
    (output / 'index.html').write_text(redirect_page('./showcase/', 'Levent · 个人网站'))
    (output / '.nojekyll').touch()
    (output / 'showcase/studio').mkdir(exist_ok=True)
    (output / 'showcase/studio/index.html').write_text(
        redirect_page(ORIGIN + '/showcase/studio/', 'Levent · 内容编辑'))
    assert not (output / 'CNAME').exists()
    report = {
        'source': PUBLIC_ROOT, 'manifest_source_files': len(manifest), 'mirrored_source_files': len(paths),
        'adapted_files': changes, 'output_files': sum(p.is_file() for p in output.rglob('*')),
        'content_snapshot': 'showcase/data/showcase-content.json',
        'backend_origin': ORIGIN, 'custom_domain': None,
        'files': {str(p.relative_to(output)): digest(p.read_bytes())
                  for p in output.rglob('*') if p.is_file()}}
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / '_site')
    parser.add_argument('--cache', type=Path, default=ROOT / '.build-cache')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = build(args.output.resolve(), args.cache.resolve())
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'files'}, indent=2))
