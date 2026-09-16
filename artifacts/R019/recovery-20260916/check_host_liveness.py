from pathlib import Path
import json,datetime,subprocess
r=Path('/home/galbot/lizekai/RSI');origin=json.loads((r/'codex-account-2/continuation/active-supervisor.json').read_text());found=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
  if any(Path(x).name in {'watch.py','learn_door_skill.py','learn_simple_task.py'} for x in args):
   found.append({'pid':int(p.name),'argv':args,'stat_start_ticks':int((p/'stat').read_text().split(') ',1)[1].split()[19])})
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
s=Path('/proc')/str(origin['pid'])/'stat';live=s.exists() and int(s.read_text().split(') ',1)[1].split()[19])==origin['start_ticks']
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'tmux server-hosted shell /proc, outside tool sandbox PID namespace','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'supervisor_origin_same_process_alive':live,'recorded_origin':origin,'matching_processes_all_separate_owners':found,'tmux_sessions':subprocess.run(['tmux','list-sessions','-F','#{session_name}'],capture_output=True,text=True,check=True).stdout.splitlines()}
report['simple_watcher_count']=sum(any(x in {str(r/'codex-account-2/continuation/watch.py'),'codex-account-2/continuation/watch.py'} for x in a['argv']) for a in found)
q=r/'artifacts/R019/recovery-20260916/live-handoff-liveness.json';q.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
assert live and report['boot_id']==origin['boot_id'];assert report['simple_watcher_count']==1
