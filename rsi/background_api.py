"""Load only the background transport pinned by a central release."""
import hashlib
import importlib.util
from pathlib import Path
from rsi.actor_transport import atomic,modules

ROOT=Path('/home/galbot/lizekai/RSI')

def episode_sender(release,output):
    relative=release['api_transport_source'];path=(ROOT/relative).resolve()
    if (not path.is_relative_to(ROOT)
            or hashlib.sha256(path.read_bytes()).hexdigest()!=release['runtime_code_hashes'][relative]):
        raise ValueError('Background transport source not admitted')
    spec=importlib.util.spec_from_file_location('admitted_background_responses',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    actor,_,_=modules()
    def publish(fields):
        index=fields['local_request_index']
        if type(index) is not int or index<1:raise ValueError('Positive local request index required')
        atomic(Path(output)/'background-requests'/f'{index:06d}.json',fields)
    return module.BackgroundResponses(actor.encoded,actor.validate_endpoint,publish)
