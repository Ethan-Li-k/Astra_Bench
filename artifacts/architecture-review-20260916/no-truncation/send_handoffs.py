from pathlib import Path
import json,datetime,hashlib,subprocess
B=Path(__file__).resolve().parent
records=[]
for entry in json.loads((B/'delivery.json').read_text()):
 name=entry['recipient'];path=B/'handoff'/f'{name}.txt';message=path.read_text()
 args=['/home/galbot/lizekai/RSI/codex-account-2/run.sh','queue','--thread',entry['thread'],'--message',message,'-m','gpt-6-astra','-c','model_reasoning_effort="xhigh"']
 p=subprocess.run(args,text=True,capture_output=True)
 receipt=p.stdout+p.stderr
 (B/'handoff'/f'{name}-queue-receipt.txt').write_text(receipt)
 records.append(dict(recipient=name,thread=entry['thread'],at=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=p.returncode,receipt=receipt,message_sha256=hashlib.sha256(message.encode()).hexdigest(),queued=p.returncode==0 and 'Queued message' in receipt,acknowledged=False,integrated=False,physical_validated=False,scope='existing authorized auxiliary queue only; no resume'))
 (B/'handoff/delivery-receipt.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
 print(name,p.returncode,receipt.strip())
 if 'usageLimitExceeded' in receipt:
  print('STOP: usageLimitExceeded; no retry/fallback');break
