"""Back up the isolated project database and media, then verify a temporary restore."""
import json
import os
import subprocess
import tarfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from dotenv import dotenv_values
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[1]
config=dotenv_values(ROOT/'.env')
url=urlparse(config['DATABASE_URL'])
if url.hostname!='127.0.0.1' or url.port!=55432 or url.path!='/legion':raise SystemExit('This command only backs up the isolated local project DB on port 55432.')
BIN=Path(os.getenv('PG_BIN','C:/Program Files/PostgreSQL/18/bin'))
timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup=ROOT/'backups';backup.mkdir(exist_ok=True)
dump=backup/f'legion-{timestamp}.dump';archive=backup/f'media-{timestamp}.tar.gz'
env={**os.environ,'PGPASSWORD':url.password}
args=['--host',url.hostname,'--port',str(url.port),'--username',url.username]
subprocess.run([str(BIN/'pg_dump.exe'),*args,'--format=custom','--no-owner','--no-acl','--file',str(dump),'legion'],env=env,check=True,capture_output=True)
with tarfile.open(archive,'w:gz') as tar:tar.add(ROOT/'media',arcname='media')
with tarfile.open(archive,'r:gz') as tar:media_count=sum(m.isfile() for m in tar.getmembers())
restore_name='legion_restore_verify_'+timestamp.lower()
admin=psycopg.connect(host=url.hostname,port=url.port,user=url.username,password=url.password,dbname='postgres',autocommit=True)
created=False
try:
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restore_name)));created=True
    subprocess.run([str(BIN/'pg_restore.exe'),*args,'--no-owner','--no-acl','--exit-on-error','--dbname',restore_name,str(dump)],env=env,check=True,capture_output=True)
    with psycopg.connect(host=url.hostname,port=url.port,user=url.username,password=url.password,dbname=restore_name) as restored:
        counts={table:restored.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table))).fetchone()[0] for table in ['cars_car','locations_city','cars_carimage']}
    assert counts=={'cars_car':91,'locations_city':4,'cars_carimage':302},counts
finally:
    # Preserve even the verification database: this rebuild explicitly forbids deletion.
    admin.close()
report={'timestamp_utc':timestamp,'database':dump.name,'media':archive.name,'database_sha256':hashlib.sha256(dump.read_bytes()).hexdigest(),'media_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'restore_verified':True,'restore_database_retained':restore_name,'restored_counts':counts,'media_files':media_count,'scope':'local development DB and imported media; not legacy production DB'}
(backup/f'manifest-{timestamp}.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(ROOT/'backup_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
