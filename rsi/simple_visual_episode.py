"""Host-only saved native scene binding; optional existing Isaac capture seam."""
import copy,hashlib,importlib,json,sys
from pathlib import Path
from urllib.parse import urlsplit

TARGETS={'simple/G1WholebodyXMovePickTeleop-v0':('0','cracker_box'),
         'simple/G1WholebodyTabletopGraspMP-v0':('10','chips_can')}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_scene(path,expected,env_id):
    path=Path(path).resolve()
    if sha(path)!=expected:raise ValueError('Scene contract changed')
    c=json.loads(path.read_text())
    if env_id not in TARGETS or c['env_id']!=env_id or c['contract'] not in ('saved-native-learning-v1','saved-native-isaac-learning-v1'):
        raise ValueError('Exact reviewed saved-scene contract required')
    source=Path(c['source']['path']);row=c['source']['index']
    if type(row) is not int or row<0 or sha(source)!=c['source']['sha256']:
        raise ValueError('Saved native source changed')
    cfg=json.loads(json.loads(source.read_text().splitlines()[row])['environment_config'])
    if hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=c['configuration_sha256']:
        raise ValueError('Saved native configuration changed')
    uid,label=TARGETS[env_id]
    target={'res_id':'graspnet1b','uid':uid,'label':label}
    if c['target']!=target or any(cfg['dr_state_dict']['target'][k]!=v for k,v in target.items()):
        raise ValueError('Saved target differs from the reviewed task')
    if c['contract']=='saved-native-isaac-learning-v1':
        # This frozen renderer is validated for the Sonic XMovePick asset only.
        if env_id!='simple/G1WholebodyXMovePickTeleop-v0':raise ValueError('Unvalidated Isaac robot variant')
        release=Path(c['renderer']['release']).resolve()
        if sha(release/'manifest.json')!=c['renderer']['manifest_sha256']:raise ValueError('Isaac release changed')
        for rel,expected_hash in json.loads((release/'manifest.json').read_text())['files'].items():
            p=(release/rel).resolve()
            if release not in p.parents or sha(p)!=expected_hash:raise ValueError('Isaac capture source changed')
        url=urlsplit(c['renderer']['endpoint'])
        if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost') or url.username or url.password or url.path or url.query or url.fragment:
            raise ValueError('Pinned local renderer endpoint required')
    elif 'renderer' in c or c.get('render_backend')!='MuJoCo':
        raise ValueError('Saved-scene renderer must be explicit')
    return c,{'state_dict':copy.deepcopy(cfg),'dr_level':None}

def verify_target(backend,contract):
    actual=backend.env.task.state_dict()['dr_state_dict']['target']
    if any(actual[k]!=v for k,v in contract['target'].items()):
        raise ValueError('Actual reset target differs from saved-scene contract')

def capture_factory(contract,output,label):
    directory=Path(contract['renderer']['release'])/'isaac_live'
    for name in ('factory','client','protocol','sonic_frame_alignment','unique_object_names'):
        if name in sys.modules and Path(sys.modules[name].__file__).resolve()!=(directory/(name+'.py')).resolve():
            raise ValueError('Foreign renderer module: '+name)
    sys.path.insert(0,str(directory))
    factory=importlib.import_module('factory')
    if Path(factory.__file__).resolve()!=(directory/'factory.py').resolve():raise ValueError('Foreign Isaac factory')
    return factory.image_capture_factory(env_id=contract['env_id'],output=output,
        endpoint=contract['renderer']['endpoint'],label=label)
