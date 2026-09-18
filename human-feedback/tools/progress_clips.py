"""One CPU encoder for bounded, public, sparse observation previews. Never input MP4.
No inference/physics, no recorder mutation. Immutable outputs; source-time captions.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,os,re,shutil,subprocess,threading,time
from pathlib import Path
from api_progress import signature

class ProgressClips:
    def __init__(self,cache):
        self.root=Path(cache);self.root.mkdir(parents=True,exist_ok=True)
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='public-keyframes')
        self.lock=threading.Lock();self.states={};self.jobs={}
    def close(self):self.pool.shutdown(wait=True)
    def request(self,d,episode,key):
        if not re.fullmatch(r'simple-[a-z0-9-]+',key) or not re.fullmatch(r'episode-\d{4,8}',episode.name):return {'state':'unknown'}
        selected=[]
        for obs in reversed(d.files(episode/'rollout/episode/observations','[0-9][0-9][0-9][0-9]')):
            packet,ref=d.read(obs/'observation.json')
            if not ref:continue
            for name in ('head_stereo_left.png','head_cam.png','head_rgb.png','rgb.png'):
                p=obs/name
                try:
                    d.safe(p);st=p.stat()
                    if not 64<=st.st_size<=20*1024*1024:continue
                    with p.open('rb') as f:
                        first=f.read(8);f.seek(-12,2);last=f.read()
                    if first!=b'\x89PNG\r\n\x1a\n' or last!=b'\x00\x00\x00\x00IEND\xaeB`\x82':continue
                    selected.append({'path':str(p),'action':int(obs.name),'at':st.st_mtime,'sig':[st.st_ino,st.st_size,st.st_mtime_ns],'camera':name.removesuffix('.png')});break
                except (OSError,ValueError):continue
            if len(selected)==6:break
        selected.reverse()
        if len(selected)<2:return {'state':'waiting_observations','note':'至少两张完整公开观测才生成关键帧片段；连续录像仍待录制端封口。'}
        fingerprint=hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest();identity=key+'-'+episode.name
        with self.lock:
            state=self.states.get(identity,{})
            target=self.root/identity
            if not state:
                try:
                    saved=json.loads((target/'latest.json').read_text())
                    if re.fullmatch('[a-f0-9]{64}',saved.get('fingerprint','')):state=saved;self.states[identity]=state
                except (OSError,ValueError):pass
            future=self.jobs.get(identity)
            if state.get('fingerprint')!=fingerprint and (future is None or future.done()):
                if state.get('failed_fingerprint')!=fingerprint:
                    self.jobs[identity]=self.pool.submit(self.encode,identity,episode.name,selected,fingerprint)
            result={k:state[k] for k in ('state','label','continuous','episode','first_action','last_action','source_at','source_start_at','generated_at','camera','frame_count','duration_s','note') if k in state}
            result.update(pending=state.get('fingerprint')!=fingerprint,latest_source_at=selected[-1]['at'])
            if state.get('fingerprint'):
                path=target/(state['fingerprint']+'.mp4')
                try:
                    if path.is_symlink():raise ValueError('symlink')
                    st=path.stat();url='/media/keyframes-'+identity+'-'+state['fingerprint']+'.mp4'
                    d.media[url]=(path,signature(path));result['url']=url
                except (OSError,ValueError):result.pop('url',None)
            if not result.get('url'):result.setdefault('state','encoding');result.setdefault('note','公开关键帧片段编码中；最新单帧继续更新。')
            return result
    def encode(self,identity,episode,frames,fingerprint):
        folder=self.root/identity;folder.mkdir(exist_ok=True);stage=folder/('pending-'+fingerprint);stage.mkdir(exist_ok=True)
        try:
            entries=[]
            for i,source in enumerate(frames):
                p=Path(source['path']);copy=stage/f'{i:02d}.png';shutil.copyfile(p,copy);st=p.stat()
                if [st.st_ino,st.st_size,st.st_mtime_ns]!=source['sig']:raise ValueError('source changed')
                entries.extend([f"file '{copy.name}'",'duration 1'])
            entries.append(f"file '{len(frames)-1:02d}.png'")
            (stage/'frames.txt').write_text('\n'.join(entries)+'\n')
            output=stage/'closed.mp4'
            args=['ffmpeg','-nostdin','-v','error','-y','-f','concat','-safe','1','-i',str(stage/'frames.txt'),'-vf',
                  "scale=640:-2,drawtext=text='PUBLIC KEYFRAMES - NOT CONTINUOUS':fontsize=17:fontcolor=white:box=1:boxcolor=black@0.7:x=8:y=8",
                  '-r','10','-an','-c:v','libx264','-preset','ultrafast','-crf','25','-threads','1','-filter_threads','1','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
            subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=25)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(output)],timeout=5))
            duration=float(probe['format']['duration'])
            if duration<=0:raise ValueError('unplayable')
            os.replace(output,folder/(fingerprint+'.mp4'))
            state={'fingerprint':fingerprint,'state':'ready','label':'公开关键帧片段（稀疏观测，非连续物理录像）','continuous':False,'episode':episode,
                   'first_action':frames[0]['action'],'last_action':frames[-1]['action'],'source_at':frames[-1]['at'],
                   'source_start_at':frames[0]['at'],'generated_at':time.time(),'camera':frames[-1]['camera'],'frame_count':len(frames),'duration_s':duration,
                   'note':'每张公开策略观测停留1秒；播放时长不等于物理时长或推理耗时。原连续MP4未改动。'}
            temp=folder/'latest.json.tmp';temp.write_text(json.dumps(state,ensure_ascii=False));os.replace(temp,folder/'latest.json')
            with self.lock:self.states[identity]=state
        except Exception as e:
            with self.lock:self.states[identity]=dict(self.states.get(identity,{}),state='encoding_error',failed_fingerprint=fingerprint,note='关键帧编码未完成；保留上一片段和最新单帧。错误类别：'+type(e).__name__)
        finally:shutil.rmtree(stage,ignore_errors=True)
