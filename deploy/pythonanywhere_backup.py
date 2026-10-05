"""Scheduled PythonAnywhere backup: pg_dump + media + checksums, no deletion."""
import os
import sys
import json
import hashlib
import tarfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, unquote
from dotenv import dotenv_values


def main():
    root=Path(__file__).resolve().parents[1]
    env=dotenv_values(root/'.env.pythonanywhere')
    url=urlsplit(env.get('DATABASE_URL',''))
    if url.scheme not in ('postgresql','postgres') or not url.hostname:
        raise SystemExit('Configure DATABASE_URL in .env.pythonanywhere.')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder=root/'backups'/f'pythonanywhere-{stamp}'
    folder.mkdir(parents=True,exist_ok=False)
    folder.chmod(0o700)
    dump=folder/'database.dump';media=folder/'media.tar.gz'
    process_env={**os.environ,'PGPASSWORD':unquote(url.password or ''),'PGSSLMODE':env.get('DB_SSLMODE','prefer')}
    subprocess.run([os.environ.get('PG_DUMP','pg_dump'),'-h',url.hostname,'-p',str(url.port or 5432),'-U',unquote(url.username or ''),'-d',unquote(url.path.lstrip('/')),'--no-owner','--no-acl','-Fc','-f',str(dump)],env=process_env,check=True)
    with tarfile.open(media,'w:gz') as archive:archive.add(root/'media',arcname='media')
    checks={}
    for path in (dump,media):
        path.chmod(0o600)
        with path.open('rb') as stream:checks[path.name]=hashlib.file_digest(stream,'sha256').hexdigest()
    (folder/'checksums.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
    print(f'Backup complete: {folder.name}. Keep an off-host copy and verify restoration.')


if __name__=='__main__':main()
