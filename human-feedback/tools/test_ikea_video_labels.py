"""Two targeted classification regressions; isolated fixture, no actor or feedback calls."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from dashboard import Dashboard, RSI

OUT=RSI/'human-feedback/dashboard-upgrade/ikea-label-fix'
SAMPLE=RSI/'ikea/diagnostics/door-v1-001/video/episode.mp4'

class IKEAVideoLabelTests(unittest.TestCase):
    def projection(self, category, kind, episode, title):
        root=Path(tempfile.mkdtemp(prefix='fixture-',dir=OUT));ikea=root/'ikea';ikea.mkdir()
        relative=('diagnostics/' if category=='diagnostic' else 'campaign/')+episode+'/video/episode.mp4'
        video=ikea/relative;video.parent.mkdir(parents=True);shutil.copyfile(SAMPLE,video)
        entry={'id':episode,'episode':episode,'path':relative,'category':category,'kind':kind,'title':title,
               'completed':True,'continuous':True,'completed_at':time.time(),'sha256':hashlib.sha256(video.read_bytes()).hexdigest()}
        (ikea/'video-manifest.json').write_text(json.dumps({'schema_version':1,'videos':[entry]}))
        (ikea/'state.json').write_text(json.dumps({'actor_running':True,'backend':'MuJoCo USD-aligned derived no-latch v3','audited_successes':0,'physical_attempts':2}))
        (ikea/'actor-progress.json').write_text(json.dumps({'episode':'door-0002','phase':'inference_waiting','actions':3}))
        adapter=Dashboard(root);row=adapter.ikea()
        self.assertEqual(row['success'],0)
        self.assertEqual(row['state'],'modelwaiting')
        self.assertIn('不等同原始 USD 场景完整物理验证',row['variant'])
        self.assertNotIn('原始带锁舌',row['variant'])
        self.assertNotIn('原始无锁舌',row['variant'])
        self.assertIsNotNone(adapter.media_file(row['videos'][0]['url']))
        return row

    def test_engineering_diagnostic_remains_unscored(self):
        row=self.projection('diagnostic','diagnostic','door-diagnostic-001','工程诊断')
        v=row['videos'][0]
        self.assertEqual(v['source_kind'],'diagnostic')
        self.assertIn('工程诊断',v['task'])
        self.assertIn('不计策略成功',v['outcome'])
        self.assertIn('不计策略尝试',row['video_note'])

    def test_policy_incomplete_is_policy_not_diagnostic_or_success(self):
        row=self.projection('learning','policy_incomplete','door-0001','首个策略回合：12动作，宿主记录错误中断，非物理失败')
        v=row['videos'][0]
        self.assertEqual(v['source_kind'],'policy_incomplete')
        self.assertEqual(v['category'],'learning')
        self.assertIn('策略尝试',v['task'])
        self.assertNotIn('工程诊断',v['task'])
        self.assertIn('12动作',v['outcome'])
        self.assertIn('宿主记录错误中断',v['outcome'])
        self.assertIn('非物理失败',v['outcome'])
        self.assertIn('未审计成功',v['outcome'])
        self.assertIn('不代表任务成功或回合完整完成',row['video_note'])

if __name__=='__main__':unittest.main(verbosity=2)
