"""
SIMPLE: SIMulation-based Policy Learning and Evaluation

Copyright (c) 2025 Songlin Wei and Contributors
Licensed under the terms in LICENSE file.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from simple.core.object import Object
from simple.core.scene import Scene
from simple.core.task import Task
from simple.dr import (
    CameraDRCfg,
    DistractorDRCfg,
    LanguageDRCfg,
    LightingDRCfg,
    MaterialDRCfg,
    SpatialDRCfg,
    TabletopSceneDRCfg,
    TargetDRCfg,
)
from simple.dr.types import Box
from simple.tasks.g1_wholebody_bend_pick_and_place_teleop import (
    G1WholebodyBendPickAndPlaceTeleop,
)
from simple.tasks.g1_wholebody_handover_teleop import G1WholebodyHandoverTeleop
from simple.tasks.g1_wholebody_bend_pick_sim_to_real_teleop import (
    _G1_COLOR_FOV_Y,
    _G1_COLOR_INTRINSICS,
    _G1_DEPTH_INTRINSICS,
    _G1_DEPTH_TO_COLOR_EXTRINSICS,
)
from simple.tasks.g1_wholebody_locomotion_pick_between_tables_teleop import (
    G1WholebodyLocomotionPickBetweenTablesTaskTeleop,
)
from simple.tasks.registry import TaskRegistry
from simple.sensors import SensorCfg, StereoCameraCfg


_SIM2REAL_HEAD_STEREO: StereoCameraCfg = StereoCameraCfg(
    uid="Realsense_D435i",
    mount="eye_in_head",
    width=640,
    height=480,
    focal_length=1.93,
    fov=_G1_COLOR_FOV_Y,
    near=0.2,
    far=5,
    baseline=0.05,
    pose=dict(position=[0.0, 0.0, 0.0]),
    intrinsics=_G1_COLOR_INTRINSICS,
    depth_intrinsics=_G1_DEPTH_INTRINSICS,
    depth_to_color_extrinsics=_G1_DEPTH_TO_COLOR_EXTRINSICS,
)


@TaskRegistry.register("g1_wholebody_pick_and_place_apple_teleop")
class G1WholebodyPickAndPlaceAppleTeleop(G1WholebodyBendPickAndPlaceTeleop):
    uid: str = "g1_wholebody_pick_and_place_apple_teleop"
    label: str = "G1 TELEOP Pick and Place Apple"
    description: str = "Pick up an apple from the right side of a bowl and place it in the bowl."

    metadata: dict[str, Any] = {
        **G1WholebodyBendPickAndPlaceTeleop.metadata,
        "success_criteria": 0.2,
    }

    sensor_cfgs: dict[str, SensorCfg] = dict(
        head_stereo=_SIM2REAL_HEAD_STEREO,
    )

    dr_cfgs = dict(
        language=LanguageDRCfg(
            instructions=[
                "pick up the apple and place it in the bowl.",
            ]
        ),
        target=TargetDRCfg(asset_id="graspnet1b:12"),
        container=TargetDRCfg(asset_id="graspnet1b:6"),
        distractors=DistractorDRCfg(
            res_id="graspnet1b",
            number_of_distractors=0,
            allow_duplicates=False,
            exclude=["12", "6"],
        ),
        spatial=SpatialDRCfg(
            spatial_mode="random",
            robot_region=Box(low=[-0.60, 0.0, 0.0], high=[-0.66, 0.0, 0.0]),
            target_region=Box(low=[-0.33, -0.12], high=[-0.29, -0.10]),
            container_region=Box(low=[-0.28, 0.04], high=[-0.28, 0.04]),
            distractors_region=[
                Box(low=[-0.32, -0.38], high=[0.03, -0.17]),
                Box(low=[-0.32, 0.24], high=[0.03, 0.38]),
                Box(low=[-0.04, -0.12], high=[0.03, 0.12]),
                Box(low=[-0.34, 0.24], high=[-0.23, 0.38]),
            ],
            target_stable_indices=[0],
            target_rotate_z=Box(low=-0.15, high=0.15),
            container_rotate_z=Box(low=1.57, high=1.59),
            placement_attempts=500,
        ),
        camera=CameraDRCfg(
            cam_id="head_stereo",
        ),
        scene=TabletopSceneDRCfg(
            scene_mode="random",
            table_size=Box(low=[0.40, 0.80, 0.015], high=[0.40, 0.80, 0.015]),
            table_position=Box(low=[-0.17, 0.0], high=[-0.17, 0.0]),
            table_height=Box(low=0.7575, high=0.7575),
            rotation_z=Box(low=0.0, high=0.0),
            room_choices=["hssd:scene0"],
            scene_manager="hssd",
            randomize_scene_pose=False,
        ),
        lighting=LightingDRCfg(
            light_mode="random",
            light_num=(2, 3),
            light_color_temperature=Box(low=6001, high=8001),
            light_intensity=Box(low=1e4*0.8, high=1e4*1.2),
            light_radius=Box(0.08, 0.12),
            light_length=Box(0.51, 2.1),
            light_spacing=Box((1.0, 1.0), (2.5, 2.5)),
            light_position=Box((-1.1, -1.1, 1.3), (1.1, 1.1, 1.5)),
            light_eulers=Box((0, 0, -0.5 * np.pi), (0, 0, 0.5 * np.pi)),
        ),
        material=MaterialDRCfg(
            material_mode="rand_objects",
            table_material={
                "path": "data/vMaterials_2/Paint/Paint_Eggshell.mdl",
                "name": "Paint_Eggshell_White",
            },
        ),
    )

    def __init__(
        self,
        robot_uid: str = "g1_sonic",
        scene_uid: str | Scene = "hssd:scene0",
        target_object: str | Object = "graspnet1b:12",
        container_object: str | Object = "graspnet1b:6",
        *args,
        **kwargs,
    ):
        self.dr_cfgs = deepcopy(type(self).dr_cfgs)
        self.robot_cfg = deepcopy(type(self).robot_cfg)
        super().__init__(
            robot_uid=robot_uid,
            scene_uid=scene_uid,
            target_object=target_object,
            container_object=container_object,
            *args,
            **kwargs,
        )


@TaskRegistry.register("g1_wholebody_handover_sim_to_real_teleop")
class G1WholebodyHandoverSimToRealTeleop(G1WholebodyHandoverTeleop):
    uid: str = "g1_wholebody_handover_sim_to_real_teleop"
    label: str = "G1 Wholebody Handover Sim-to-Real Teleop"
    description: str = (
        "Teleoperation task for handing over a tabletop object in the measured "
        "sim-to-real table setup."
    )

    metadata: dict[str, Any] = {
        **G1WholebodyHandoverTeleop.metadata,
        "success_criteria": 0.5,
    }

    sensor_cfgs: dict[str, SensorCfg] = dict(
        head_stereo=_SIM2REAL_HEAD_STEREO,
    )

    dr_cfgs = dict(
        language=LanguageDRCfg(
            instructions=[
                "hand over the {} from the right hand to the left hand.",
            ]
        ),
        target=TargetDRCfg(asset_id="graspnet1b:0"),
        spatial=SpatialDRCfg(
            spatial_mode="random",
            robot_region=Box(low=[-0.60, 0.0, 0.0], high=[-0.66, 0.0, 0.0]),
            target_region=Box(low=[-0.28, -0.05], high=[-0.24, 0.03]),
            target_stable_indices=[0],
            target_rotate_z=Box(low=-0.15, high=0.15),
            placement_attempts=500,
        ),
        camera=CameraDRCfg(
            cam_id="head_stereo",
        ),
        scene=TabletopSceneDRCfg(
            scene_mode="random",
            table_size=Box(low=[0.40, 0.80, 0.015], high=[0.40, 0.80, 0.015]),
            table_position=Box(low=[-0.17, 0.0], high=[-0.17, 0.0]),
            table_height=Box(low=0.7575, high=0.7575),
            rotation_z=Box(low=0.0, high=0.0),
            room_choices=["hssd:scene0"],
            scene_manager="hssd",
            randomize_scene_pose=False,
        ),
        lighting=LightingDRCfg(
            light_mode="random",
            light_num=(2, 3),
            light_color_temperature=Box(low=6001, high=8001),
            light_intensity=Box(low=1e4*0.8, high=1e4*1.2),
            light_radius=Box(0.08, 0.12),
            light_length=Box(0.51, 2.1),
            light_spacing=Box((1.0, 1.0), (2.5, 2.5)),
            light_position=Box((-1.1, -1.1, 1.3), (1.1, 1.1, 1.5)),
            light_eulers=Box((0, 0, -0.5 * np.pi), (0, 0, 0.5 * np.pi)),
        ),
        material=MaterialDRCfg(
            material_mode="rand_objects",
            table_material={
                "path": "data/vMaterials_2/Paint/Paint_Eggshell.mdl",
                "name": "Paint_Eggshell_White",
            },
        ),
    )

    def __init__(
        self,
        robot_uid: str = "g1_sonic",
        scene_uid: str | Scene = "hssd:scene0",
        target_object: str | Object = "graspnet1b:0",
        *args,
        **kwargs,
    ):
        self.dr_cfgs = deepcopy(type(self).dr_cfgs)
        self.robot_cfg = deepcopy(type(self).robot_cfg)
        super().__init__(
            robot_uid=robot_uid,
            scene_uid=scene_uid,
            target_object=target_object,
            *args,
            **kwargs,
        )

    def state_dict(self):
        return Task.state_dict(self)

    def check_success(self, info: dict[str, Any], *args, **kwargs) -> bool:
        reward = self.compute_reward(info, *args, **kwargs)
        return reward >= self.success_criteria

    def check_wether_handover_success(self, *args, **kwargs) -> bool:
        target_name = str(self.target.asset.label)
        mujoco_env = kwargs.get("mujoco_env", None)
        if mujoco_env is None:
            return False

        mj_physics_data = mujoco_env.mjData
        mj_physics_model = mujoco_env.mjModel

        for i_contact in range(mj_physics_data.ncon):
            contact = mj_physics_data.contact[i_contact]
            g1 = mj_physics_model.geom(contact.geom1)
            g2 = mj_physics_model.geom(contact.geom2)
            body1 = mj_physics_model.body(g1.bodyid).name
            body2 = mj_physics_model.body(g2.bodyid).name

            if (target_name in body1 and "left_hand" in body2) or (
                target_name in body2 and "left_hand" in body1
            ):
                return True
        return False

    def compute_reward(self, info: dict[str, Any], *args, **kwargs) -> float:
        if self.check_wether_handover_success(*args, **kwargs):
            self.reward += 0.1
        else:
            self.reward = 0.0
        return self.reward

    def decompose(self):
        from simple.datagen.subtask_spec import (
            GraspObjectSpec,
            LiftSpec,
            OpenGripperSpec,
            PhaseBreakSpec,
            StandSpec,
        )

        return [
            StandSpec("initialize"),
            PhaseBreakSpec("phase_break_before_right_grasp", grasp_type="bodex"),
            GraspObjectSpec(
                "right_grasp_object",
                target_uid=self.target.uid,
                pregrasp=False,
                grasp_type="bodex",
                hand_uid="dex3_right",
                lock_links=["left_hand_palm_link"],
            ),
            LiftSpec("lift", up=0.08, grasp_type="bodex", hand_uid="dex3_right"),
            PhaseBreakSpec("phase_break_before_left_grasp", grasp_type="bodex"),
            GraspObjectSpec(
                "left_grasp_object",
                target_uid=self.target.uid,
                pregrasp=False,
                grasp_type="bodex",
                hand_uid="dex3_left",
                lock_links=[
                    "right_hand_palm_link",
                    "right_hand_index_1_link",
                    "right_hand_middle_1_link",
                    "right_hand_thumb_2_link",
                ],
                keep_force=True,
            ),
            OpenGripperSpec("release_right", grasp_type="bodex", hand_uid="dex3_right"),
            StandSpec("stop"),
        ]


@TaskRegistry.register("g1_wholebody_handover_place_back_sim_to_real_teleop")
class G1WholebodyHandoverPlaceBackSimToRealTeleop(G1WholebodyHandoverSimToRealTeleop):
    uid: str = "g1_wholebody_handover_place_back_sim_to_real_teleop"
    label: str = "G1 Wholebody Handover Place Back Sim-to-Real Teleop"
    description: str = (
        "Teleoperation task for handing a Cheez-It box from the right hand to "
        "the left hand, then placing it back on the sim-to-real table."
    )

    metadata: dict[str, Any] = {
        **G1WholebodyHandoverSimToRealTeleop.metadata,
        "success_criteria": 1.0,
    }

    dr_cfgs = deepcopy(G1WholebodyHandoverSimToRealTeleop.dr_cfgs)
    dr_cfgs["language"] = LanguageDRCfg(
        instructions=[
            "hand over the cheezit from the right hand to the left hand, then place it back on the table.",
        ]
    )

    def __init__(
        self,
        robot_uid: str = "g1_sonic",
        scene_uid: str | Scene = "hssd:scene0",
        target_object: str | Object = "graspnet1b:0",
        *args,
        **kwargs,
    ):
        self._right_grasp_seen = False
        self._handover_completed = False
        super().__init__(
            robot_uid=robot_uid,
            scene_uid=scene_uid,
            target_object=target_object,
            *args,
            **kwargs,
        )

    def reset(
        self, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> None:
        super().reset(seed, options)
        self._right_grasp_seen = False
        self._handover_completed = False

    def check_target_hand_contact(self, hand_name: str, *args, **kwargs) -> bool:
        mujoco_env = kwargs.get("mujoco_env", None)
        if mujoco_env is None:
            return False

        target_name = str(self.target.asset.label)
        mj_physics_data = mujoco_env.mjData
        mj_physics_model = mujoco_env.mjModel

        for i_contact in range(mj_physics_data.ncon):
            contact = mj_physics_data.contact[i_contact]
            g1 = mj_physics_model.geom(contact.geom1)
            g2 = mj_physics_model.geom(contact.geom2)
            body1 = mj_physics_model.body(g1.bodyid).name
            body2 = mj_physics_model.body(g2.bodyid).name

            target_hand_contact = (
                (target_name in body1 and hand_name in body2)
                or (target_name in body2 and hand_name in body1)
            )
            if target_hand_contact:
                return True
        return False

    def update_handover_progress(self, *args, **kwargs) -> None:
        if self.check_target_hand_contact("right_hand", *args, **kwargs):
            self._right_grasp_seen = True
        if self._right_grasp_seen and self.check_target_hand_contact(
            "left_hand", *args, **kwargs
        ):
            self._handover_completed = True

    def check_target_on_table_top(self, *args, **kwargs) -> bool:
        mujoco_env = kwargs.get("mujoco_env", None)
        if mujoco_env is None:
            return False

        table = self.layout.actors.get("table")
        if table is None:
            return False

        target_name = str(self.target.asset.label)
        table_top_z = table.pose.position[2] + 0.5 * table.size[2]
        top_face_tolerance = 0.02

        mj_physics_data = mujoco_env.mjData
        mj_physics_model = mujoco_env.mjModel

        for i_contact in range(mj_physics_data.ncon):
            contact = mj_physics_data.contact[i_contact]
            g1 = mj_physics_model.geom(contact.geom1)
            g2 = mj_physics_model.geom(contact.geom2)
            body1 = mj_physics_model.body(g1.bodyid).name
            body2 = mj_physics_model.body(g2.bodyid).name

            target_table_contact = (
                (target_name in body1 and body2 == "table")
                or (target_name in body2 and body1 == "table")
            )
            if (
                target_table_contact
                and abs(contact.pos[2] - table_top_z) <= top_face_tolerance
            ):
                return True
        return False

    def check_success(self, info: dict[str, Any], *args, **kwargs) -> bool:
        self.update_handover_progress(*args, **kwargs)
        return (
            self._handover_completed
            and self.check_target_on_table_top(*args, **kwargs)
            and not self.check_hand_object_contact(*args, **kwargs)
        )

    def compute_reward(self, info: dict[str, Any], *args, **kwargs) -> float:
        self.reward = 1.0 if self.check_success(info, *args, **kwargs) else 0.0
        return self.reward

    def decompose(self):
        from simple.datagen.subtask_spec import (
            GraspObjectSpec,
            LiftSpec,
            LowerSpec,
            MoveEEFToPoseSpec,
            OpenGripperSpec,
            PhaseBreakSpec,
            StandSpec,
        )

        import transforms3d as t3d

        table = self.layout.actors["table"]
        table_top_z = table.pose.position[2] + 0.5 * table.size[2]
        target_xy = np.array(self.target.pose.position[:2])
        place_position = np.array([target_xy[0], target_xy[1], table_top_z + 0.14])
        place_orientation = t3d.euler.euler2quat(0, 0, 0)

        return [
            StandSpec("initialize"),
            PhaseBreakSpec("phase_break_before_right_grasp", grasp_type="bodex"),
            GraspObjectSpec(
                "right_grasp_object",
                target_uid=self.target.uid,
                pregrasp=False,
                grasp_type="bodex",
                hand_uid="dex3_right",
                lock_links=["left_hand_palm_link"],
            ),
            LiftSpec("lift_right", up=0.08, grasp_type="bodex", hand_uid="dex3_right"),
            PhaseBreakSpec("phase_break_before_left_grasp", grasp_type="bodex"),
            GraspObjectSpec(
                "left_grasp_object",
                target_uid=self.target.uid,
                pregrasp=False,
                grasp_type="bodex",
                hand_uid="dex3_left",
                lock_links=[
                    "right_hand_palm_link",
                    "right_hand_index_1_link",
                    "right_hand_middle_1_link",
                    "right_hand_thumb_2_link",
                ],
                keep_force=True,
            ),
            OpenGripperSpec("release_right", grasp_type="bodex", hand_uid="dex3_right"),
            MoveEEFToPoseSpec(
                "move_left_to_table",
                position=place_position,
                orientation=place_orientation,
                grasp_type="bodex",
                hand_uid="dex3_left",
                lock_links=["right_hand_palm_link"],
            ),
            LowerSpec(
                "lower_left_to_table",
                down=0.08,
                grasp_type="bodex",
                hand_uid="dex3_left",
            ),
            OpenGripperSpec("release_left", grasp_type="bodex", hand_uid="dex3_left"),
            StandSpec("stop"),
        ]


@TaskRegistry.register("g1_wholebody_mobile_pick_and_place_cheezit_teleop")
class G1WholebodyMobilePickAndPlaceCheezitTeleop(
    G1WholebodyLocomotionPickBetweenTablesTaskTeleop
):
    uid: str = "g1_wholebody_mobile_pick_and_place_cheezit_teleop"
    label: str = "G1 TELEOP Mobile Pick and Place Cheezit"
    description: str = (
        "Pick up a Cheez-It box, move to a second table offset by 90 degrees, "
        "and place it on the second table."
    )

    metadata: dict[str, Any] = {
        **G1WholebodyLocomotionPickBetweenTablesTaskTeleop.metadata,
        "max_episode_steps": 1200,
    }

    sensor_cfgs: dict[str, SensorCfg] = dict(
        head_stereo=_SIM2REAL_HEAD_STEREO,
    )

    dr_cfgs = dict(
        language=LanguageDRCfg(
            instructions=[
                "pick up the cheezit from the first table, move to the second table, and place it on the second table.",
            ]
        ),
        target=TargetDRCfg(asset_id="graspnet1b:0"),
        spatial=SpatialDRCfg(
            spatial_mode="random",
            robot_region=Box(low=[-0.60, 0.0, 0.0], high=[-0.66, 0.0, 0.0]),
            target_region=Box(low=[-0.28, -0.05], high=[-0.24, 0.03]),
            target_stable_indices=[0],
            target_rotate_z=Box(low=-0.15, high=0.15),
            placement_attempts=500,
            obj_surface_map={
                "target": "table",
            },
        ),
        camera=CameraDRCfg(
            cam_id="head_stereo",
        ),
        scene=TabletopSceneDRCfg(
            scene_mode="random",
            table_size=Box(low=[0.40, 0.80, 0.015], high=[0.40, 0.80, 0.015]),
            table_position=Box(low=[-0.17, 0.0], high=[-0.17, 0.0]),
            table_height=Box(low=0.7575, high=0.7575),
            rotation_z=Box(low=0.0, high=0.0),
            table2_size=Box(low=[0.40, 0.80, 0.015], high=[0.40, 0.80, 0.015]),
            table2_position=Box(low=[-1.22, 1.28], high=[-1.22, 1.28]),
            table2_height=Box(low=0.7575, high=0.7575),
            table2_rotation_z=Box(low=np.pi / 2, high=np.pi / 2),
            room_choices=["hssd:scene0"],
            scene_manager="hssd",
            enable_table2=True,
            randomize_scene_pose=False,
        ),
        lighting=LightingDRCfg(
            light_mode="random",
            light_num=(2, 3),
            light_color_temperature=Box(low=6001, high=8001),
            light_intensity=Box(low=1e4*0.8, high=1e4*1.2),
            light_radius=Box(0.08, 0.12),
            light_length=Box(0.51, 2.1),
            light_spacing=Box((1.0, 1.0), (2.5, 2.5)),
            light_position=Box((-1.1, -1.1, 1.3), (1.1, 1.1, 1.5)),
            light_eulers=Box((0, 0, -0.5 * np.pi), (0, 0, 0.5 * np.pi)),
        ),
        material=MaterialDRCfg(
            material_mode="rand_objects",
            table_material={
                "path": "data/vMaterials_2/Paint/Paint_Eggshell.mdl",
                "name": "Paint_Eggshell_White",
            },
        ),
    )

    def __init__(
        self,
        robot_uid: str = "g1_sonic",
        scene_uid: str | Scene = "hssd:scene14",
        target_object: str | Object = "graspnet1b:0",
        *args,
        **kwargs,
    ):
        self.dr_cfgs = deepcopy(type(self).dr_cfgs)
        self.robot_cfg = deepcopy(type(self).robot_cfg)
        super().__init__(
            robot_uid=robot_uid,
            scene_uid=scene_uid,
            target_object=target_object,
            *args,
            **kwargs,
        )

    def check_target_on_table2_top(self, *args, **kwargs) -> bool:
        mujoco_env = kwargs.get("mujoco_env", None)
        if mujoco_env is None:
            return False

        table2 = self.layout.actors.get("table2")
        if table2 is None:
            return False

        target_name = str(self.target.asset.label)
        table2_top_z = table2.pose.position[2] + 0.5 * table2.size[2]
        top_face_tolerance = 0.02

        mj_physics_data = mujoco_env.mjData
        mj_physics_model = mujoco_env.mjModel

        for i_contact in range(mj_physics_data.ncon):
            contact = mj_physics_data.contact[i_contact]
            g1 = mj_physics_model.geom(contact.geom1)
            g2 = mj_physics_model.geom(contact.geom2)
            body1 = mj_physics_model.body(g1.bodyid).name
            body2 = mj_physics_model.body(g2.bodyid).name

            target_table2_contact = (
                (target_name in body1 and "table2" in body2)
                or (target_name in body2 and "table2" in body1)
            )
            if (
                target_table2_contact
                and abs(contact.pos[2] - table2_top_z) <= top_face_tolerance
            ):
                return True
        return False

    def check_success(self, info: dict[str, Any], *args, **kwargs) -> bool:
        return (
            self.check_target_on_table2_top(*args, **kwargs)
            and not self.check_hand_object_contact(*args, **kwargs)
        )

    def compute_reward(self, info: dict[str, Any], *args, **kwargs) -> float:
        self.reward = 1.0 if self.check_success(info, *args, **kwargs) else 0.0
        return self.reward

    def decompose(self):
        from simple.datagen.subtask_spec import (
            GraspObjectSpec,
            LiftSpec,
            OpenGripperSpec,
            PhaseBreakSpec,
            StandSpec,
            TurnSpec,
            WalkSpec,
        )

        return [
            StandSpec("initialize"),
            PhaseBreakSpec("phase_break_before_grasp", grasp_type="bodex"),
            GraspObjectSpec(
                "grasp_object",
                target_uid=self.target.uid,
                pregrasp=False,
                grasp_type="bodex",
                hand_uid="dex3_right",
                lock_links=["left_hand_palm_link"],
            ),
            LiftSpec("lift", up=0.08, grasp_type="bodex", hand_uid="dex3_right"),
            TurnSpec("turn_to_second_table", vx=0.1, target_yaw=np.pi / 2),
            WalkSpec(
                "walk_to_second_table",
                vx=0.25,
                vy=0.15,
                target_yaw=np.pi / 2,
                target_distance=1.50,
            ),
            OpenGripperSpec("release", hand_uid="dex3_right"),
            StandSpec("stop", target_yaw=np.pi / 2),
        ]
