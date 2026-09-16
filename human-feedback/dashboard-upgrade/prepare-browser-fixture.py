from pathlib import Path
import sys,json,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'tools'))
from dashboard import Dashboard,RSI
from feedback_board import FeedbackBoard
from store import immutable
root=Path(__file__).resolve().parent/'fixture-browser-delivery';src=root/'sources'
for n in (1,2,3):
 e=src/'artifacts/R019/apple-campaign'/f'episode-{n:04d}'
 (e/'video').mkdir(parents=True,exist_ok=True);(e/'rollout/episode/observations/0001').mkdir(parents=True,exist_ok=True)
 shutil.copyfile(RSI/'human-feedback/reproductions/H001/evidence/closure-lift-head-left.mp4',e/'video/episode.mp4')
 shutil.copyfile(RSI/'artifacts/R019/apple-campaign/episode-0007/rollout/episode/observations/0122/head_stereo_left.png',e/'rollout/episode/observations/0001/head_stereo_left.png')
 (e/'rollout/episode/observations/0001/observation.json').write_text(json.dumps({'sim_s':1,'fixture':True}))
 (e/'result.json').write_text(json.dumps({'terminal_kind':'physical_failure','actions':1,'human_feedback_used':False,'fixture':True}))
 (e/'failure_review.json').write_text(json.dumps({'independent_reset_verified':True,'no_replay_or_diagnostic_initial_state':True,'reset':{'reset_id':'synthetic-reset-'+str(n)},'control_version':'fixture-v1','mechanism':'fixture-grasp','fixture':True}))
d=Dashboard(src);d.snapshot();b=FeedbackBoard(d,root/'feedback',fixture=True)
c={'case_id':'HC-browser-fixture','task_id':'simple','title':'工程合成测试：三次独立失败问题（非生产结论）','mechanism':'fixture-grasp','control_version':'fixture-v1','question':'工程测试：你认为先调整高度还是深度？','choices':['先调整高度','先调整深度'],'facts':'这是一组隔离的合成测试元数据，借用旧录像测试播放器。','hypothesis':'仅测试问题展示，不声称三次实际失败。','already_tried':'三个独立fixture reset用于资格校验，不能记入真实任务。','unresolved':True,'attempts':[]}
for rid,rec in d.records.items():
 evidence=d.case_media(rid);c['attempts'].append({'record_id':rid,'result_sha256':rec['result_sha256'],'reset_id':rec['reset_id'],'video_url':evidence['video']['url'],'keyframe_url':evidence['preview']['url'],'timestamps':[1,3],'change':'合成测试','outcome':'合成终态'})
b.validate_case(c);p=b.root/'cases'/(c['case_id']+'.json')
if not p.exists():immutable(p,c)
print(root)
