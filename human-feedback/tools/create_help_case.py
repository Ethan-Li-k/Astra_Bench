#!/usr/bin/env python3
"""Validate and append one eligible public intervention case; no model calls."""
import argparse,json
from pathlib import Path
from dashboard import Dashboard
from feedback_board import FeedbackBoard
from store import immutable
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);a=p.parse_args()
    d=Dashboard();d.snapshot();b=FeedbackBoard(d);case=json.loads(a.input.read_text());validated=b.validate_case(case)
    target=b.root/'cases'/(validated['case_id']+'.json');immutable(target,case)
    print(json.dumps({'saved':str(target),'version':validated['version']},ensure_ascii=False))
