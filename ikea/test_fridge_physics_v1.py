"""Synthetic counterexamples only; no simulated attempts or success scores."""
import copy
import unittest
from review_fridge_physics_v1 import physical_audit


def samples():
    rows=[]
    for i in range(110):
        angle=min(.9,i*.045);contact=i<25
        rows.append(dict(sim_s=(i+1)*.02,base_z=.75,tilt_rad=.1,stable=True,safety_reason=None,
            doors=dict(left=dict(open_rad=angle,hand_contact=contact),right=dict(open_rad=0.,hand_contact=False)),
            contacts=[dict(door='left',robot_body='right_hand_thumb_2_link',normal_force_n=2.)] if contact else []))
    return rows


class FridgeAuditTests(unittest.TestCase):
    def test_valid_same_door_contact_and_final_hold(self):
        r=physical_audit(samples(),0.);self.assertTrue(r['passed']);self.assertEqual(r['qualified_doors'],['left'])

    def test_left_contact_cannot_support_right_opening(self):
        rows=samples()
        for row in rows:row['doors']['right']['open_rad']=row['doors']['left']['open_rad'];row['doors']['left']['open_rad']=0.
        self.assertFalse(physical_audit(rows,0.)['passed'])

    def test_probe_is_not_robot_hand(self):
        rows=samples()
        for row in rows:
            for contact in row['contacts']:contact['robot_body']='fridge_probe'
        self.assertFalse(physical_audit(rows,0.)['passed'])

    def test_reclosure_erases_terminal_qualification(self):
        rows=samples();rows[-1]['doors']['left']['open_rad']=.2
        result=physical_audit(rows,0.);self.assertFalse(result['passed']);self.assertGreater(result['maximum_hold_s']['left'],1.)

    def test_unstable_final_hold_rejected(self):
        rows=samples();rows[-1]['base_z']=.4;rows[-1]['stable']=False
        self.assertFalse(physical_audit(rows,0.)['passed'])

    def test_missing_tick_rejected(self):
        rows=samples();rows.pop(20);self.assertFalse(physical_audit(rows,0.)['passed'])

    def test_contact_after_motion_does_not_prove_driving(self):
        rows=samples()
        for i,row in enumerate(rows):
            on=i>=30;row['doors']['left']['hand_contact']=on
            row['contacts']=[dict(door='left',robot_body='left_hand_middle_1_link',normal_force_n=1.)] if on else []
        self.assertFalse(physical_audit(rows,0.)['passed'])


if __name__=='__main__':unittest.main()
