"""Static robot/action compatibility and inherited criteria; zero episode credit."""
import argparse
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import simple.envs  # registrations only
from simple.tasks.registry import TaskRegistry
from simple.robots.registry import RobotRegistry
from rsi.scalebfm import METADATA


def xml_joints(path, visited=None):
    visited = set() if visited is None else visited
    path = path.resolve()
    if path in visited: return set()
    visited.add(path)
    root = ET.parse(path).getroot()
    names = {e.attrib['name'] for e in root.iter('joint') if 'name' in e.attrib}
    for include in root.iter('include'):
        names.update(xml_joints(path.parent/include.attrib['file'], visited))
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True,exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    inventory=json.loads((root/'artifacts/R019/task-inventory.json').read_text())
    policy=set(json.loads(METADATA.read_text())['joint_names'])
    rows=[]
    for entry in inventory['entries']:
        if entry['kwargs']['task'] not in TaskRegistry._registry:
            rows.append({'env_id':entry['id'],'status':'task_not_registered_by_native_import',
                'registered_gym_entry':entry['entry_point'],'task_definition':entry.get('task_definition'),
                'missing_task_key':entry['kwargs']['task'],'success_credit':0,'physics_action_calls':0,
                'gpt_calls':0,'robot_uid':'unresolved'})
            continue
        task=TaskRegistry._registry[entry['kwargs']['task']]
        robot_uid=task.robot_cfg['uid']
        robot=RobotRegistry._registry[robot_uid]
        asset=root/'data/simple/runtime'/robot.mjcf_path
        row={'env_id':entry['id'],'task_class':task.__name__,'robot_uid':robot_uid,
             'entry_point':entry['entry_point'],'source':inspect.getfile(task),
             'robot_source':inspect.getfile(robot),'robot_asset':str(asset),
             'native_sonic':entry['native_sonic'],'physics_action_calls':0,'gpt_calls':0,
             'success_credit':0,'inherited_criteria':{}}
        try:
            missing=sorted(policy-xml_joints(asset))
            row['missing_model_38000_joints']=missing
            if missing:
                row['status']='robot_topology_incompatible_with_model_38000'
            elif entry['native_sonic']:
                row['status']='native_bridge_preflight_available'
            else:
                row['status']='legacy_g1_action_bridge_not_implemented'
                row['limitation']='Registered environment uses LocoManipulationEnv and a legacy robot controller, not the native Sonic decoupled_wbc 20ms action path. This is not a runtime unavailability verdict.'
        except Exception as error:
            row['status']='static_asset_audit_blocked';row['error']=f'{type(error).__name__}: {error}'
        for name in dir(task):
            if name=='compute_reward' or name.startswith('check_'):
                method=getattr(task,name)
                if not callable(method):continue
                try:
                    source=inspect.getsource(method)
                    owner=next(c.__name__ for c in task.__mro__ if name in c.__dict__)
                    row['inherited_criteria'][name]={'owner':owner,'file':inspect.getfile(method),
                        'line':inspect.getsourcelines(method)[1],'source':source,
                        'sha256':hashlib.sha256(source.encode()).hexdigest()}
                except (OSError,TypeError,StopIteration):pass
        rows.append(row)
    report={'actor_access':False,'scope':'Static compatibility and inherited reward definitions; no runtime task success and no task removed',
            'registered_count':len(rows),'status_counts':dict(Counter(r['status'] for r in rows)),
            'robot_counts':dict(Counter(r['robot_uid'] for r in rows)),'entries':rows}
    (args.output/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='entries'}),flush=True)


if __name__=='__main__':main()
