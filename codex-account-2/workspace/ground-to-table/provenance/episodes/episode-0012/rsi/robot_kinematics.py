"""Robot-only FK landmarks and static frame conventions; never object state."""
UPPER_BODY_LINKS = ('torso_link','left_shoulder_pitch_link','left_elbow_link',
                    'left_wrist_yaw_link','right_shoulder_pitch_link','right_elbow_link',
                    'right_wrist_yaw_link')


def upper_body_world(model,data):
    return {name:{'position_world_m':data.xpos[model.body(name).id].tolist(),
                  'quaternion_wxyz':data.xquat[model.body(name).id].tolist()}
            for name in UPPER_BODY_LINKS}


def upper_body_conventions(model):
    bodies=set()
    for name in UPPER_BODY_LINKS:
        bid=model.body(name).id
        while bid:
            bodies.add(bid);bid=int(model.body_parentid[bid])
    rows=[]
    for bid in sorted(bodies):
        parent=int(model.body_parentid[bid]);joints=[]
        for j in range(int(model.body_jntadr[bid]),int(model.body_jntadr[bid]+model.body_jntnum[bid])):
            if int(model.jnt_type[j])!=3:continue # Hinge joints only; root pose is measured.
            joints.append({'name':model.joint(j).name,'axis_body':model.jnt_axis[j].tolist(),
                'position_body_m':model.jnt_pos[j].tolist(),'range_rad':model.jnt_range[j].tolist(),
                'reference_rad':float(model.qpos0[model.jnt_qposadr[j]])})
        rows.append({'name':model.body(bid).name,'parent':model.body(parent).name if parent else None,
            'position_parent_m':model.body_pos[bid].tolist(),'quaternion_parent_wxyz':model.body_quat[bid].tolist(),
            'hinge_joints':joints})
    return {'meaning':'Original known robot frame/joint geometry only. Measured pelvis pose supplies the root transform. Joint scalar zero is not an anatomical straight-arm definition.',
            'bodies':rows}
