"""Inventory actual ENVS file opens from the audited terminal runs."""
import json,re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
audit=json.loads((root/'outputs/TEXTURE-RUNTIME-AUDIT-072.json').read_text())
catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text())
expected={a['archive'] for a in catalog['archives'] if a['archive'].startswith('ENVS/')}
observed={}
for name in audit['runs']:
    for line in (root/'work/runs'/name/'native.log').read_text().splitlines():
        if '[io] raw UMD open' not in line:continue
        match=re.search(r'\\(ENVS\\[^\"]+)"',line)
        if match:observed.setdefault(match.group(1).replace('\\','/'),set()).add(name)
report=dict(scope='Successful audited runs with actual environment-file opens. An open does not prove traversal, visual correctness, all textures rendered, or every scenario completed.',audited_runs=len(audit['runs']),catalogued_env_archives=len(expected),observed_env_archives={p:sorted(names) for p,names in sorted(observed.items())},unobserved_env_archives=sorted(expected-observed.keys()))
(root/'outputs/TEXTURE-RUNTIME-COVERAGE-072.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['# Runtime environment coverage — checkpoint 072','',f"{len(observed)} environment archives were opened across {len(audit['runs'])} audited successful runs. The archive catalog contains {len(expected)} ENVS files. Opens are not full traversal or rendering acceptance.",'','| Environment archive | Audited runs |','| --- | --- |']
lines += [f"| {path} | {', '.join(sorted(names))} |" for path,names in sorted(observed.items())]
lines += ['','The accompanying JSON explicitly lists unobserved environment archives. Campaign, era and map variants remain separate paths.','']
(root/'outputs/TEXTURE-RUNTIME-COVERAGE-072.md').write_text('\n'.join(lines))
print(json.dumps(dict(observed_env_archives=len(observed),unobserved_env_archives=len(expected-observed.keys()))))
