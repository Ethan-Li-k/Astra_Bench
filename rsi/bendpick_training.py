"""Exact BendPickSim learning completion; preserve its native event and controls."""
from rsi.simple_grasp_mp import RetainedGraspEvaluator,CONTRACT as RETAINED
ENV='simple/G1WholebodyBendPickSimToRealTeleop-v0'
CONTRACT=dict(RETAINED,id='bendpick-sim-retained-clear-lift-v1',scope=ENV,
              native_criterion='original native height event retained; event alone does not terminate')

class BendPickTrainingEvaluator(RetainedGraspEvaluator):
    def __init__(self):
        self.env_id=ENV
        self.task_uid='g1_wholebody_bend_pick_sim_to_real_teleop'
        self.completion_contract=CONTRACT
    def host_audit_state(self):
        return dict(super().host_audit_state(),contract=CONTRACT['id'])
