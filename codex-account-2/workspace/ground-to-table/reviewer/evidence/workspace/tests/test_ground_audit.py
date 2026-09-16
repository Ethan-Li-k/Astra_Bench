"""Adversarial traces, not demonstrations and never inputs to the actor."""
import copy
import unittest
from ground_task import PhaseAudit

def initial():
    return dict(t=0.,cube=[.65,.2,.025],cube_bottom=0.,pelvis=[0.,0.,.75],
        feet=[[0,.1,0],[0,-.1,0]],foot_contact=[True,True],foot_clearance=[0.,0.],
        floor_contact=True,table_contact=False,hand_contact=False,grasped=False,
        inside_table=False,hand_clearance=1.,cube_speed=0.,cube_angular_speed=0.,
        standing=True,invalid=None)

def advance(a,s,n=1):
    for _ in range(n):
        s['t']+=.02;a.update(copy.deepcopy(s))

def walk(a,s):
    for i in range(2):
        s['foot_contact'][i]=False;s['foot_clearance'][i]=.03
        s['feet'][i][0]=.24;s['pelvis'][0]=.22
        advance(a,s,8)
        s['foot_contact'][i]=True;s['foot_clearance'][i]=0.
        advance(a,s,8)

class Counterexamples(unittest.TestCase):
    def test_initial_table_rejected(self):
        s=initial();s['cube_bottom']=.63
        with self.assertRaises(ValueError): PhaseAudit(s)

    def test_wrist_or_lean_is_not_locomotion(self):
        s=initial();a=PhaseAudit(copy.deepcopy(s));s['pelvis'][0]=.3
        advance(a,s,30)
        self.assertFalse(a.phase['locomotion'])

    def test_sliding_both_feet_is_not_walking(self):
        s=initial();a=PhaseAudit(copy.deepcopy(s));s['pelvis'][0]=.3
        for f in s['feet']:f[0]=.3
        advance(a,s,30)
        self.assertFalse(a.phase['locomotion'])

    def test_pushed_or_thrown_cube_fails(self):
        s=initial();a=PhaseAudit(copy.deepcopy(s));walk(a,s)
        s.update(cube_bottom=.63,floor_contact=False,table_contact=True,inside_table=True)
        advance(a,s,110)
        self.assertFalse(a.result()['overall_success'])

    def test_grasp_requires_prior_movement(self):
        s=initial();a=PhaseAudit(copy.deepcopy(s))
        s.update(grasped=True,floor_contact=False,cube_bottom=.1)
        advance(a,s,30)
        self.assertFalse(a.phase['ground_grasp'])

    def complete_until_release(self):
        s=initial();a=PhaseAudit(copy.deepcopy(s));walk(a,s)
        s.update(grasped=True,hand_contact=True,floor_contact=False,cube_bottom=.1)
        advance(a,s,30)
        s['cube'][0]+=.2;advance(a,s)
        return a,s

    def test_held_on_table_fails(self):
        a,s=self.complete_until_release()
        s.update(table_contact=True,inside_table=True,cube_bottom=.63)
        advance(a,s,110)
        self.assertFalse(a.phase['table_release_hold'])

    def test_short_hold_or_edge_placement_fails(self):
        a,s=self.complete_until_release()
        s.update(table_contact=True,inside_table=True,hand_contact=False,grasped=False)
        advance(a,s,70)
        self.assertFalse(a.phase['table_release_hold'])
        s['inside_table']=False;advance(a,s,110)
        self.assertFalse(a.phase['table_release_hold'])

    def test_invalid_state_always_fails(self):
        for invalid in ('external_state_write','model_or_dynamics_changed','external_force'):
            a,s=self.complete_until_release();s['invalid']=invalid;advance(a,s)
            self.assertFalse(a.result()['overall_success']);self.assertEqual(a.invalid,invalid)

    def test_dropped_target_cannot_bridge_transport(self):
        a,s=self.complete_until_release()
        s.update(grasped=False,floor_contact=True)
        advance(a,s)
        self.assertFalse(a.phase['transport'])

    def test_success_must_still_hold_at_final_frame(self):
        a,s=self.complete_until_release()
        s.update(table_contact=True,inside_table=True,hand_contact=False,grasped=False)
        advance(a,s,110)
        self.assertTrue(a.result()['overall_success'])
        s['inside_table']=False;advance(a,s)
        self.assertFalse(a.result()['overall_success'])

    def test_full_ordered_audit_can_pass(self):
        a,s=self.complete_until_release()
        s.update(table_contact=True,inside_table=True,hand_contact=False,grasped=False)
        advance(a,s,110)
        self.assertTrue(a.result()['overall_success'])
        s['standing']=False;advance(a,s)
        self.assertFalse(a.result()['overall_success'])

if __name__=='__main__':unittest.main()
