"""Make the user-approved nine-second three-still montage; no generated 3D frames.

FFmpeg is a project-local build dependency (imageio-ffmpeg in .local/video-tools).
The three supplied images remain untouched. The result is a dissolve montage,
not a reconstructed continuous camera orbit.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.local/video-tools'))
import imageio_ffmpeg
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
OUT=ROOT/'static/video';OUT.mkdir(exist_ok=True)
SOURCES=[ROOT/'design_refs/3d'/name for name in ['01-start.png','02-scroll-50.png','03-end-headlights.png']]
target=OUT/'hero-reference.mp4'
filters=[]
for i,anchor in enumerate(['iw-iw/zoom','(iw-iw/zoom)/2','0']):
    # Oversampling prevents subpixel crop shimmer during the very small push-in.
    filters.append(f'[{i}:v]scale=3200:1800:flags=lanczos,setsar=1,zoompan=z=1+0.012*on/107:x={anchor}:y=ih-ih/zoom:d=108:s=1600x900:fps=30,trim=duration=3.6,setpts=PTS-STARTPTS,fps=30,settb=1/30,format=yuv420p[v{i}]')
filters += ['[v0][v1]xfade=transition=fade:duration=0.9:offset=2.7,fps=30,settb=1/30[x1]','[x1][v2]xfade=transition=fade:duration=0.9:offset=5.4,fps=30,format=yuv420p[out]']
command=[FFMPEG,'-hide_banner','-loglevel','warning','-y']
for source in SOURCES:command+=['-i',str(source)]
command+=['-filter_complex',';'.join(filters),'-map','[out]','-an','-t','9','-c:v','libx264','-preset','slow','-crf','23','-profile:v','high','-level','4.0','-pix_fmt','yuv420p','-g','15','-keyint_min','15','-sc_threshold','0','-movflags','+faststart',str(target)]
subprocess.run(command,check=True)
poster=ROOT/'static/img/hero-video-poster.webp'
subprocess.run([FFMPEG,'-hide_banner','-loglevel','error','-y','-i',str(target),'-frames:v','1','-c:v','libwebp','-quality','82',str(poster)],check=True)
mobile_poster=ROOT/'static/img/hero-video-mobile.webp'
subprocess.run([FFMPEG,'-hide_banner','-loglevel','error','-y','-i',str(target),'-vf','crop=1050:620:550:260,scale=720:-2:flags=lanczos','-frames:v','1','-c:v','libwebp','-quality','79',str(mobile_poster)],check=True)
preview=ROOT/'output/playwright/hero-video';preview.mkdir(parents=True,exist_ok=True)
for name,time in [('front',0),('profile',4.5),('rear',8.8)]:
    subprocess.run([FFMPEG,'-hide_banner','-loglevel','error','-y','-ss',str(time),'-i',str(target),'-frames:v','1',str(preview/f'frame-{name}.png')],check=True)
hashof=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
frames=imageio_ffmpeg.read_frames(str(target))
metadata=next(frames)
frames.close()
report={'kind':'Three supplied stills, cross-dissolves and 1.2% push-in; not a continuous 3D rotation','user_authorization':'2026-10-03: assemble video from the three reference frames with smooth transitions','sources':[{'path':str(p.relative_to(ROOT)),'sha256':hashof(p)} for p in SOURCES],'duration_seconds':9,'fps':30,'resolution':[1600,900],'audio':False,'keyframe_interval_frames':15,'transition_seconds':.9,'timeline':[{'start':0,'end':2.7,'view':'front'},{'start':2.7,'end':3.6,'view':'dissolve front to profile'},{'start':3.6,'end':5.4,'view':'profile'},{'start':5.4,'end':6.3,'view':'dissolve profile to rear'},{'start':6.3,'end':9,'view':'rear and lights'}],'video':{'path':str(target.relative_to(ROOT)),'bytes':target.stat().st_size,'sha256':hashof(target)},'poster':{'path':str(poster.relative_to(ROOT)),'bytes':poster.stat().st_size,'sha256':hashof(poster)},'ffmpeg_version':imageio_ffmpeg.get_ffmpeg_version()}
report['mobile_poster']={'path':str(mobile_poster.relative_to(ROOT)),'bytes':mobile_poster.stat().st_size,'sha256':hashof(mobile_poster)}
report['target_duration_seconds']=9
report['duration_seconds']=metadata['duration']
(ROOT/'reports/hero_video_asset.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False),flush=True)
