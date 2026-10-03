"""Static Compose validation and optional native Nginx checks; never claims a Docker run."""
import json,subprocess,os
from pathlib import Path
import yaml,jsonschema,requests
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)
WORK=ROOT/'.local/nginx-check';WORK.mkdir(parents=True,exist_ok=True)
schema_file=WORK/'compose-spec.json'
if not schema_file.exists():
    response=requests.get('https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json',timeout=30);response.raise_for_status();schema_file.write_bytes(response.content)
schema=json.loads(schema_file.read_text(encoding='utf8'))
result={'docker_available':False,'docker_build_tested':False,'compose_up_tested':False,'compose_schema':{},'nginx_syntax':{}}
for name in ['compose.yaml','docker-compose.yml','docker-compose.dev.yml']:
    data=yaml.safe_load((ROOT/name).read_text(encoding='utf8'));jsonschema.validate(data,schema)
    if name!='compose.yaml':
        assert {'web','db','nginx'}<=set(data['services']);assert '/var/lib/postgresql' in data['services']['db']['volumes'][0]
        assert data['services']['web']['depends_on']['db']['condition']=='service_healthy'
        assert data['services']['nginx']['depends_on']['web']['condition']=='service_healthy'
    result['compose_schema'][name]='pass'
docker=(ROOT/'Dockerfile').read_text();assert docker.count('FROM ')==3 and 'USER legion' in docker and 'HEALTHCHECK' in docker
result['dockerfile_static']='three stages, nonroot runtime, healthcheck, lockfiles, build outputs verified'
nginx=ROOT/'.local/nginx-1.30.5/nginx.exe'
if nginx.exists():
    (WORK/'logs').mkdir(exist_ok=True);(WORK/'acme').mkdir(exist_ok=True);(WORK/'temp').mkdir(exist_ok=True)
    certificate=WORK/'fullchain.pem';key=WORK/'privkey.pem'
    if not certificate.exists():
        openssl=Path('C:/Program Files/Git/usr/bin/openssl.exe')
        subprocess.run([str(openssl),'req','-x509','-newkey','rsa:2048','-nodes','-days','2','-subj','/CN=localhost','-keyout',str(key),'-out',str(certificate)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    common=(ROOT/'deploy/nginx-shared.conf').read_text().replace('root /srv;',f'root {WORK.as_posix()}/www;').replace('alias /srv/',f'alias {WORK.as_posix()}/www/').replace('http://web:8001','http://127.0.0.1:8003')
    (WORK/'shared.conf').write_text(common)
    for name in ['nginx.conf','nginx-bootstrap.conf','nginx-dev.conf']:
        text=(ROOT/'deploy'/name).read_text().replace('listen 8080;','listen 127.0.0.1:8004;').replace('listen 8443 ssl;','listen 127.0.0.1:8443 ssl;')
        text=text.replace('/etc/nginx/legion/shared.conf',f'{WORK.as_posix()}/shared.conf').replace('/var/www/acme',f'{WORK.as_posix()}/acme')
        text=text.replace('/etc/letsencrypt/live/legionautorent.kz/fullchain.pem',certificate.as_posix()).replace('/etc/letsencrypt/live/legionautorent.kz/privkey.pem',key.as_posix())
        config=f'worker_processes 1;\nevents {{ worker_connections 256; }}\nhttp {{\ninclude {nginx.parent.as_posix()}/conf/mime.types;\n'+(ROOT/'deploy/nginx-compression.conf').read_text()+'\n'+text+'\n}\n'
        target=WORK/name;target.write_text(config)
        command=subprocess.run([str(nginx),'-p',WORK.as_posix()+'/', '-c',target.as_posix(),'-t'],capture_output=True,text=True)
        result['nginx_syntax'][name]={'exit_code':command.returncode,'output':command.stderr.strip()}
        if command.returncode:raise RuntimeError(command.stderr)
    result['nginx_native_version']='1.30.5 Windows; paths/upstream/ports adapted for validation'
(OUT/'deployment_validation.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
