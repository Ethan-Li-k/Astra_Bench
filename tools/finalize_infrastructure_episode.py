"""Finish only the skill review of a naturally completed, infrastructure-stopped episode."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from rsi.codex_app_server import CodexPolicyAdapter
from rsi.stdio_transport import StdioAppServer
from rsi.skill_learning import SkillMemory
from tools.learn_grasp_skill import LearningHost, CODEX_LAUNCHER


class TerminalReviewHost(LearningHost):
    def tool_specs(self):
        return [s for s in super().tool_specs() if s['name'] in ('experience_read','skill_update')]

    def dispatch(self,name,arguments):
        if name not in ('experience_read','skill_update'):
            raise ValueError('Physical runtime is closed. Only terminal evidence review is available.')
        return super().dispatch(name,arguments)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--episode',type=Path,required=True)
    args=p.parse_args();episode=args.episode.resolve();campaign=episode.parent
    original=json.loads((episode/'result.json').read_text())
    boundary=json.loads((episode/'infrastructure_boundary_stop.json').read_text())
    assert boundary['status']=='safe_complete_turn_boundary' and not boundary['unmatched_turn_start']
    assert not original['skill_updated'] and original['error'] and original['actions']>0
    root=episode/'terminal_review';root.mkdir(exist_ok=False)
    (episode/'infrastructure_original_result.json').write_text(json.dumps(original,indent=2)+'\n')
    old_context=json.loads((episode/'agent/workspace.json').read_text())
    public={'rollout_finished':True,'native_outcome':original['native_outcome'],
        'stop_reason':'backend_execution_error','physical_actions':original['actions'],
        'sim_s':original['sim_s'],'success':False,
        'why':'The next continuous request was admitted but not physically executed: floating point subtraction made its legal 3s gripper ramp slightly greater than3s, then an admitted command blocked subsequent requests. Runtime closed only after all started model turns completed. This is an infrastructure failure, not evidence that the proposed sidestep failed physically.',
        'review_scope':'Use only original public observations/execution receipts. No new physics or human feedback. Preserve pending task hypotheses and distinguish the single confirmed yaw chunk from rejected requests. The host repaired duration arithmetic for future independent resets; no gait or lever result is supplied.'}
    evidence=episode/'rollout/execution_error.json';evidence.write_text(json.dumps(public,indent=2)+'\n')
    memory=SkillMemory(campaign/'memory',Path(old_context['skill']))
    host=TerminalReviewHost(episode,memory,episode.name,old_context['successes_so_far'])
    host.finished=True;host.stop_reason='backend_execution_error'
    host.harness=SimpleNamespace(evaluator=SimpleNamespace(outcome=lambda _:original['native_outcome']))
    host.skill_sources=old_context['skill_sources']
    selections=[json.loads(s) for s in (episode/'rollout/skill_selection.jsonl').read_text().splitlines()]
    host.selected_source_ids=selections[-1]['selected_ids']
    agent=root/'agent';agent.mkdir();(agent/'scratch').mkdir()
    context=dict(old_context,terminal_review_only=True,physical_tools_available=False,
                 infrastructure_termination=public,evidence_for_revision=str(evidence))
    (agent/'workspace.json').write_text(json.dumps(context,indent=2)+'\n')
    skill=memory.skill.read_text();(agent/'SKILL.md').write_text(skill)
    (root/'model_backend.json').write_text(json.dumps({'launcher':str(CODEX_LAUNCHER),
        'account_route':'authorized_account_2','model':'gpt-6-astra','effort':'xhigh',
        'fallback':False,'role':'same_episode_terminal_policy_review','physical_actions_available':False},indent=2))
    transport=StdioAppServer([str(CODEX_LAUNCHER),'app-server','--stdio'],root/'app_server')
    adapter=CodexPolicyAdapter(transport,host,agent,normal_tools=True,
        developer_instructions=skill+'\nThis is the terminal review of the SAME infrastructure-stopped physical episode, not a new campaign or physical attempt. Read workspace.json. The host has confirmed rollout_finished=true. Only experience_read and skill_update are available. Do not inspect simulator/evaluator code, hidden object/contact state or other experiments. Use only this episode/campaign public evidence and previously listed self-experience. Submit a concise task_specific skill_update within831 words/6250 characters/5357 non-whitespace. Do not claim rejected requests were executed or skill success. Do not recreate an environment. Full inference is awaited.')
    try:
        adapter.connect()
        while not host.skill_updated:
            if adapter.turns_started>=3:raise RuntimeError('Three complete terminal-review turns without revision; preserve evidence and stop retries.')
            turn=adapter.run_turn('Complete the evidence-backed skill revision for this terminated episode. Read workspace.json, experience_read and public execution_error.json. Host next_call: '+json.dumps(host.next_call()))
            (root/f'turn_{adapter.turns_started:03d}.json').write_text(json.dumps(turn,indent=2)+'\n')
        result=dict(original,skill_updated=True,stop_reason='backend_execution_error',
            terminal_review={'path':str(root),'turns':adapter.turns_started,'full_turn_completed':turn['status']=='completed',
                             'new_physical_actions':0,'model':'gpt-6-astra','effort':'xhigh'},
            error='BackendExecutionError: admitted legal3s reference rejected by gripper duration rounding; original runtime closed at complete-turn boundary.')
        (episode/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        (root/'result.json').write_text(json.dumps({'skill_updated':True,'full_turn_completed':turn['status']=='completed',
            'physical_attempt_credit':False,'task_success_credit':False,'new_physical_actions':0},indent=2)+'\n')
        print(json.dumps(result),flush=True)
    finally:transport.close()


if __name__=='__main__':main()
