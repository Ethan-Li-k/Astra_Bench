"""Next-run API bridge only. Registration changes never reset or act on physics."""
import hashlib
import json
import threading
from pathlib import Path


class SerialBatchContinuation:
    """Preserve one host/history while exact registered batches change serially.

    The caller owns the live host, PublicHistory and global public-tool numbering.
    A replacement factory must register a fresh scoped batch through the existing
    maintainer interface and construct a transport session with no request sent.
    This helper grants no extra financial authorization and never sends/retries.
    """
    def __init__(self,session,host,replacement_factory,journal):
        self.session,self.host=session,host
        self.replacement_factory=replacement_factory
        self.journal=Path(journal)
        self.seen={session.run_id}
        self.lock=threading.Lock()
        self.stopped=False

    def ready(self,*,phase='policy'):
        if not self.lock.acquire(blocking=False):
            raise RuntimeError('Concurrent batch transition forbidden')
        try:
            if self.stopped:raise RuntimeError('Batch bridge stopped; no automatic retry')
            if phase not in ('policy','terminal_review'):
                raise ValueError('Unknown continuation phase')
            old=self.session
            if old.stopped:raise RuntimeError('Old session stopped or ambiguous; no transition')
            if old.count<old.max_calls:return old
            host=self.host
            if host.execution_error or host.initialization_error or host.backend.active is not None:
                raise RuntimeError('Physical action or host error prevents transition')
            if host.finished and phase!='terminal_review':
                raise RuntimeError('Terminal episode requires its explicit review/conclusion route')
            if not host.finished and phase=='terminal_review':
                raise RuntimeError('Terminal review requires an actual terminal episode')
            receipt_path=old.output/f'{old.count:02d}'/'receipt.json'
            receipt=json.loads(receipt_path.read_text())
            if not (receipt.get('state')=='completed' and receipt.get('finished_at_unix') is not None
                    and receipt.get('returned_model')=='gpt-6-astra'
                    and isinstance(receipt.get('returned_reasoning'),dict)
                    and receipt['returned_reasoning'].get('effort')=='xhigh'
                    and receipt.get('http_status')==200):
                raise RuntimeError('Only a verified completed previous response permits transition')
            before=(id(host.backend),id(host.harness),host.actions,float(host.backend.data.time))
            evidence=dict(previous_run=old.run_id,previous_call=old.count,
                previous_response_id=receipt.get('response_id'),previous_receipt=str(receipt_path),
                previous_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                episode=host.episode_id,actions=host.actions,absolute_sim_s=float(host.backend.data.time),
                phase=phase,allowed_terminal_tool='conclude' if phase=='terminal_review' else None,
                reason='local_registered_batch_count_only',old_unknown_fees_retained=True)
            # Registration/transport creation is the sole mutation here, and has
            # no callback argument exposing the simulation object.
            new=self.replacement_factory(evidence)
            after=(id(host.backend),id(host.harness),host.actions,float(host.backend.data.time))
            if before!=after:raise RuntimeError('Registration unexpectedly changed physical state')
            if new.run_id in self.seen or new.count!=0 or new.stopped:
                raise RuntimeError('Replacement must be a unique unsent registered session')
            evidence.update(new_run=new.run_id,new_max_calls=new.max_calls,
                same_reset=True,physics_advanced=False,request_sent=False)
            self.journal.parent.mkdir(parents=True,exist_ok=True)
            with self.journal.open('a') as stream:stream.write(json.dumps(evidence)+'\n')
            self.seen.add(new.run_id);self.session=new
            return new
        except BaseException:
            self.stopped=True
            raise
        finally:self.lock.release()
