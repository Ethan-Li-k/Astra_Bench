import unittest
from human_gate import assess

def attempt(n,**changes):
    row=dict(episode=f'e{n}',reset=f'r{n}',mechanism='loaded_foot_no_lift',
        control_signature='frozen-A',new_physics=True,exploration=True,
        complete=True,actions=2,success=False,terminal_kind='physical_failure',video=f'e{n}.mp4',
        evidence=f'e{n}/result.json',tested_change=f'hypothesis-{n}')
    row.update(changes)
    return row

class HumanGateTests(unittest.TestCase):
    def check(self,rows,expected,review=True):
        self.assertEqual(assess(rows,'loaded_foot_no_lift','frozen-A',review)['can_ask_human'],expected)
    def test_two_attempts_rejected(self):self.check([attempt(1),attempt(2)],False)
    def test_duplicate_reset_rejected(self):self.check([attempt(1),attempt(2,reset='r1'),attempt(3)],False)
    def test_duplicate_episode_rejected(self):self.check([attempt(1),attempt(2,episode='e1'),attempt(3)],False)
    def test_reproduction_not_new_exploration(self):self.check([attempt(1),attempt(2),attempt(3,exploration=False)],False)
    def test_different_control_not_pooled(self):self.check([attempt(1),attempt(2),attempt(3,control_signature='B')],False)
    def test_missing_video_rejected(self):self.check([attempt(1),attempt(2),attempt(3,video=None)],False)
    def test_unreviewed_cluster_rejected(self):self.check([attempt(1),attempt(2),attempt(3)],False,False)
    def test_three_complete_comparable_failures(self):self.check([attempt(1),attempt(2),attempt(3)],True)
    def test_early_exit_budget_and_infra_not_physical_failure(self):
        for kind in ('agent_stopped_incomplete','budget_limited_incomplete','infrastructure_error',None):
            self.check([attempt(1),attempt(2),attempt(3,terminal_kind=kind)],False)

if __name__=='__main__':unittest.main()
