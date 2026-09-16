from pathlib import Path
import urllib.request,json,datetime,signal,os
r=Path('/home/galbot/lizekai/RSI');out=r/'human-feedback/dashboard-upgrade'
def get(url):
 with urllib.request.urlopen(url,timeout=10) as response:return response.status,json.load(response)
code,health=get('http://127.0.0.1:8765/api/health');assert code==200 and health['mode']=='four_task_feedback' and health['fixture'] is False
code,data=get('http://127.0.0.1:8765/api/dashboard');assert len(data['tasks'])==4;data.pop('csrf',None)
media=[]
for t in data['tasks']:
 for d in [t]+t.get('subtasks',[]):
  for v in d.get('videos',[]):
   req=urllib.request.Request('http://127.0.0.1:8765'+v['url'],headers={'Range':'bytes=64-127'})
   with urllib.request.urlopen(req,timeout=10) as res:
    assert res.status==206 and len(res.read())==64
    media.append({'url':v['url'],'range':res.headers['Content-Range']})
closed=[]
for port in [8766,8767,8768]:
 _,h=get(f'http://127.0.0.1:{port}/api/health');assert h.get('fixture') is True
 pid=h['pid'];argv=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0');assert b'--fixture-root' in argv and str(out).encode() in argv[argv.index(b'--fixture-root')+1]
 assert str(port).encode() in argv;os.kill(pid,signal.SIGTERM);closed.append({'port':port,'pid':pid,'fixture':True})
(out/'live-public-delivery.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
(out/'service-verification.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'health':health,'dynamic_range_verified':media,'fixture_servers_stopped':closed,'production_kept_running':True,'production_answer_count':len(data['answers']),'public_case_count':data['help']['eligible_count']},ensure_ascii=False,indent=2))
print(json.dumps({'health':health,'media_range_checks':len(media),'production_answers':len(data['answers']),'closed_fixtures':closed},ensure_ascii=False))
