"""Create an isolated developer cluster using existing PostgreSQL binaries."""
import os
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(os.getenv('PG_BIN', 'C:/Program Files/PostgreSQL/18/bin'))
LOCAL = ROOT / '.local'
LOCAL.mkdir(exist_ok=True)
if (ROOT / '.env').exists():
    raise SystemExit('Existing .env preserved. Configure the isolated cluster manually.')
password = secrets.token_hex(24)
pwfile = LOCAL / 'init-password'
pwfile.write_text(password, encoding='ascii')
try:
    subprocess.run([str(BIN / 'initdb.exe'), '-D', str(LOCAL / 'postgres'), '-U', 'legion_dev', '--pwfile', str(pwfile), '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C'], check=True)
finally:
    pwfile.unlink(missing_ok=True)
(ROOT / '.env').write_text(f'ENVIRONMENT=development\nDEBUG=true\nSECRET_KEY={secrets.token_urlsafe(64)}\nDATABASE_URL=postgresql://legion_dev:{password}@127.0.0.1:55432/legion\nSITE_URL=https://legionautorent.kz\nALLOWED_HOSTS=localhost,127.0.0.1,testserver\nSECURE_SSL_REDIRECT=false\nANALYTICS_ENABLED=false\n', encoding='utf-8')
print('Isolated cluster initialized. Credentials stored in ignored .env; port 55432.')
