"""Generate the existing canvas as a read-only entry; no annotation framework."""
import json
from store import ROOT
from server import progress
x=progress()
source='''import { useHostTheme, H1, H2, Text, Link, Stack } from "cursor/canvas";
const DATA = __DATA__;
export default function VideoProgress() {
 const theme=useHostTheme();
 return <Stack gap={16} style={{padding:24,color:theme.text.primary,background:theme.bg.editor}}>
  <H1>RSI · 视频与进展</H1>
  <Link href="http://127.0.0.1:8765/">打开真实视频播放页（加载与seek由Chrome验证）</Link>
  <Text>人工求助关闭。H001和F001当前均无需填写；至少3次可比真实独立探索仍未解决并经审核后，才提交代表性失败。</Text>
  <H2>已有录像</H2>
  {DATA.videos.map(v=><div key={v.id}><Link href={"http://127.0.0.1:8765/#"+v.id}>{v.title}</Link><Text>{`${v.duration_s} 秒 · ${v.width}×${v.height}`}</Text><Text>{v.view}</Text><Text>{v.timing}</Text><Text>{v.result_note}</Text></div>)}
  <H2>当前状态快照</H2><Text>{DATA.h001_progress.summary}</Text><Text>{DATA.selected_frame_warning}</Text>
  <details><summary>H001 三条已导入原话</summary>{DATA.feedback.H001.replies.map(r=><div key={r.question_id}><Text>{r.question_id}</Text><Text>{r.verbatim}</Text></div>)}<Text>{DATA.feedback.H001.annotation_id}</Text></details>
  <details><summary>F001 已收到的原话</summary><Text>{DATA.feedback.F001.verbatim}</Text></details>
  <Text style={{color:theme.text.secondary}}>此副本只提供内联进展快照和视频网页链接，无表单、网络读取或标注存储。原话与human_proposed规则分开；未声明修正成功。实时状态以本地页为准。</Text>
 </Stack>;
}
'''.replace('__DATA__',json.dumps(x,ensure_ascii=False))
(ROOT/'ui/H001-feedback.canvas.tsx').write_text(source)
print('read-only canvas source updated; no renderer claim')
