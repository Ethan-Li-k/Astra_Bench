#!/usr/bin/env python3
"""Import an explicit desktop transcription; never infer human answers."""
import argparse
import json
from pathlib import Path
from store import ROOT, Store, digest


def import_payload(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('import must be inside human-feedback')
    payload = json.loads(path.read_text())
    if payload.get('phase') != 'desktop_transcription':
        raise ValueError('desktop_transcription required')
    transcripts = payload.get('transcripts', [])
    if not transcripts:
        raise ValueError('explicit source transcripts required')
    for item in transcripts:
        p = (ROOT / item['file']).resolve()
        if not p.is_relative_to(ROOT) or p.suffix != '.json' or digest(p.read_bytes()) != item['sha256']:
            raise ValueError('transcript source missing or changed')
        source = json.loads(p.read_text())
        if source.get('source') != 'explicit_user_reply_in_desktop_thread' or source.get('case_id') != 'H001' or source.get('verbatim') != item['verbatim']:
            raise ValueError('not an explicit H001 user transcript')
        if source.get('case_sha256', payload['case_sha256']) != payload['case_sha256']:
            raise ValueError('transcript case mismatch')
    for key, value in payload['answers'].items():
        if value and not any(value in t['verbatim'] for t in transcripts):
            raise ValueError('answers must preserve verbatim excerpts, not agent interpretation')
    return Store().submit(payload, channel='desktop_import')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    print(json.dumps(import_payload(args.input), ensure_ascii=False, indent=2))
