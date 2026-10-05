"""Package deployable sources and prebuilt frontend, excluding secrets and user data."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIRECTORIES=('legion','core','cars','locations','pages','seo','bookings','analytics','importer','templates','static','locale','frontend','migration','deploy','tools')
FILES=('manage.py','requirements.txt','requirements.lock','package.json','package-lock.json','vite.config.js','.env.pythonanywhere.example','PYTHONANYWHERE.md','ADMIN_GUIDE.md','README.md','seo_audit_old_site.json')


def files():
    result=[]
    for directory in DIRECTORIES:
        for path in (ROOT/directory).rglob('*'):
            if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts or path.suffix in ('.pyc','.log'):continue
            if path.name.startswith('.env'):continue
            result.append(path)
    result.extend(ROOT/name for name in FILES if (ROOT/name).is_file())
    return sorted(set(result))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if not (ROOT/'static/build/.vite/manifest.json').exists():raise SystemExit('Run npm run build before packaging.')
    if args.output.exists():raise SystemExit('Choose a new filename; existing archives are never replaced.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    paths=files()
    with tarfile.open(args.output,'x:gz') as archive:
        for path in paths:archive.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
    with args.output.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    report={'archive':args.output.name,'sha256':digest,'bytes':args.output.stat().st_size,'files':len(paths),'includes_static_build':True,'includes_media':False,'includes_credentials':False}
    args.output.with_suffix('.manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report))


if __name__=='__main__':main()
