from pathlib import Path
import json,os,signal,subprocess,time,urllib.request,datetime
r=Path('/home/galbot/lizekai/RSI');out=r/'human-feedback/dashboard-upgrade/candidate-delivery-schema'
status=json.loads((r/'human-feedback/reviews/server-status.json').read_text())
health=json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=5));pid=health['pid']
assert status['pid']==pid and health['service']=='rsi-H001-human-feedback'
argv=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
assert argv[:4]==[b'python3',b'human-feedback/tools/server.py',b'--port',b'8765'],argv
assert os.readlink(f'/proc/{pid}/cwd')==str(r)
pane=subprocess.check_output(['tmux','list-panes','-t','rsi-human-feedback-h001','-F','#{pane_pid} #{pane_start_command}']).decode()
assert 'human-feedback/tools/run_server.sh' in pane
before={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'health':health,'verified_argv':[x.decode() for x in argv if x],'pane':pane,'only_ui_pid_signaled':pid}
(out/'restart-before.json').write_text(json.dumps(before,indent=2))
os.kill(pid,signal.SIGTERM)
for i in range(50):
 if not Path(f'/proc/{pid}').exists():break
 time.sleep(.1)
assert not Path(f'/proc/{pid}').exists(),'old UI did not exit; no additional signal'
# Pipeline exits naturally; do not kill a shared tmux server or unrelated session.
for i in range(50):
 if subprocess.run(['tmux','has-session','-t','rsi-human-feedback-h001'],stderr=subprocess.DEVNULL).returncode:break
 time.sleep(.1)
assert subprocess.run(['tmux','has-session','-t','rsi-human-feedback-h001'],stderr=subprocess.DEVNULL).returncode!=0
subprocess.run(['tmux','new-session','-d','-s','rsi-human-feedback-h001','bash /home/galbot/lizekai/RSI/human-feedback/tools/run_server.sh'],check=True)
for i in range(100):
 try:
  h=json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=1))
  if h['mode']=='four_task_feedback':break
 except Exception:pass
 time.sleep(.1)
else:raise RuntimeError('new UI did not become healthy')
(out/'restart-after.json').write_text(json.dumps({'health':h,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'only_ui_restarted':True},indent=2));print(h)
