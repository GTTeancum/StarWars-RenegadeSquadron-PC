"""Preserve full-trace evidence for the Echo Base mixed-draw fallback defect."""
import hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
folder=r/'work/runs/coverage086-echo';state=json.loads((folder/'run.json').read_text())
assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
draws=[json.loads(l) for l in (folder/'world-draws.jsonl').read_text().splitlines()]
assert not any(d.get('truncated') or d.get('sample_truncated') for d in draws)
assert all(d['sample_count']==len(d['samples'])==(d['primitive']&65535) for d in draws)
diagnosis=json.loads((r/'outputs/ECHO-FULL-086.json').read_text())
selected=[]
for d in diagnosis:
 if d['draw'] not in [135,140,144,145,146,147,178]:continue
 t=d['topology'];missing=[x for x in t if x['max_vertex_error']>=.003]
 selected.append(dict(draw=d['draw'],vertices=d['primitive']&65535,exact_vertices=d['best'][0]['matched'],triangles=len(t),exact_triangles=sum(x['source_triangle'] and x['max_vertex_error']<.003 for x in t),deviating_triangles=len(missing),max_vertex_distance=max(x['max_vertex_error'] for x in t),changed_topology=sum(not x['source_triangle'] for x in t)))
report=dict(run=state,full_trace_sha256=sha(folder/'world-draws.jsonl'),trace_draws=len(draws),trace_vertices=sum(d['sample_count'] for d in draws),trace_truncated=False,diagnosis_sha256=sha(r/'outputs/ECHO-FULL-086.json'),draws=selected,tests_sha256=sha(r/'outputs/WORLD-086-tests.log'),scope='Nearest-position/topology diagnosis is evidence for a matching defect, not authorization to assign arbitrary textures or relax matching globally. No new converted replacements claimed.')
(r/'outputs/ECHO-086-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(draws=selected,trace_vertices=report['trace_vertices']),indent=2))
