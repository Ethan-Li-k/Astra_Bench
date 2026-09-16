"""No physics/model requests: exercise the actor's read/calculation boundary."""
from pathlib import Path
import json
from runner import PublicHost, OUT, public_only

h=PublicHost.__new__(PublicHost)
h.number=1;h.public=OUT/'trial-001/public'
checks={}
for label,path in {
    'host_audit':OUT/'host_audit/assessment_contract.json',
    'baseline':OUT.parents[1]/'reproductions/H001/REPORT.md',
    'traversal':h.public/'../../host_audit/assessment_contract.json',
    'account':OUT.parents[2]/'codex-account-2/home/auth.json',
}.items():
    try:h.allowed_path(str(path))
    except ValueError:checks[label]=True
    else:checks[label]=False
checks['public_source_allowed']=h.allowed_path(str(OUT/'public/sources/H001-user-feedback-003.json')).is_file()
for label,expr in {'no_file_read':"np.fromfile('/etc/passwd')",'no_import':"__import__('os')",'no_object_introspection':'(1).__class__'}.items():
    try:h.dispatch('calculate',{'expression':expr})
    except ValueError:checks[label]=True
    else:checks[label]=False
checks['numerical_allowed']=h.dispatch('calculate',{'expression':'np.linalg.norm([3, 4])'})['value']==5
checks['native_recursively_removed']=public_only({'native_outcome':'success','x':[{'reward':1,'robot':2}]})=={'x':[{'robot':2}]}
checks['no_reset_tool']='loco_start' not in {x['name'] for x in h.tool_specs()}
(OUT/'host_audit/boundary_checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks))
assert all(checks.values())
