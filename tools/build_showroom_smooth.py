"""Interpolate the supplied clean orbit to 60 fps, retaining its first/last views."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FF=ROOT/'.local/video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
SOURCE=ROOT/'design_refs/hero/hero-source.mp4'
WORK=ROOT/'review/showroom-smooth'
WORK.mkdir(parents=True,exist_ok=True)
output=WORK/'hero-60-final.mp4'
# Motion estimation needs real lookahead; cloned input frames are discarded by
# minterpolate. Keep output through 7.45s, then the exact clean source frame 179
# for the remaining two output frames. No pixels from the rejected tail ship.
filters='[0:v]split[orbit][last];[orbit]trim=end_frame=183,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,trim=end_frame=448,setpts=PTS-STARTPTS[motion];[last]trim=start_frame=179:end_frame=180,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=0.1,fps=60,trim=end_frame=2[rest];[motion][rest]concat=n=2:v=1:a=0[film]'
command=[str(FF),'-hide_banner','-loglevel','error','-n','-i',str(SOURCE),
         '-filter_complex',filters,'-map','[film]','-r','60','-c:v','libx264','-crf','20','-preset','slow',
         '-g','8','-keyint_min','8','-bf','0','-pix_fmt','yuv420p',
         '-movflags','+faststart','-an',str(output)]
if not output.exists():subprocess.run(command,check=True)
probe=subprocess.run([str(FF),'-hide_banner','-i',str(output),'-map','0:v:0','-f','null','-'],capture_output=True,text=True,check=True)
frames=int(re.findall(r'frame=\s*(\d+)',probe.stderr)[-1])
assert frames==450,probe.stderr
assert '1280x720' in probe.stderr and '60 fps' in probe.stderr
data=output.read_bytes();digest=hashlib.sha256(data).hexdigest()
assert len(data)<10_000_000
asset=ROOT/'static/hero'/f'hero-scrub-smooth60-{digest[:12]}.mp4'
if not asset.exists():asset.write_bytes(data)
report={'source':SOURCE.relative_to(ROOT).as_posix(),
        'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'asset':asset.relative_to(ROOT).as_posix(),'sha256':digest,'bytes':len(data),
        'width':1280,'height':720,'source_fps':24,'fps':60,'frames':frames,
        'duration':7.5,'last_time':449/60,'last_source_time':179/24,
        'filter':filters,'crf':20,'gop':8,'audio':False,'upscaled':False,
        'interpolated':True,'paid_generations':0,'command':command}
(ROOT/'reports/showroom_smooth_asset.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
