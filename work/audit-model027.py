"""Preserve material/cache diagnostics and exact source/build hashes."""
import hashlib
import json
import re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
report={"runs":{},"hashes":{}}
paths=["work/audit-model027.py","outputs/MODEL-027-tests.log",
       "work/project/source/profiles/renegade/host/override_model.cpp",
       "work/project/source/profiles/renegade/host/override_model.hpp",
       "work/project/source/profiles/renegade/tests/override_model.cpp",
       "work/project/source/profiles/vcs/host/ge_renderer.cpp",
       "work/build-windows-native/bin/RenegadeNative.exe",
       "work/model024-geonosis-replay.txt"]
paths += [p.relative_to(root).as_posix() for p in
          (root/"work/mods-model027/models/cis_logo_blue").iterdir() if p.is_file()]
for name in ("model027-cis","model027-cache-fixed"):
    folder=root/"work/runs"/name
    run=json.loads((folder/"run.json").read_text())
    assert run["state"]=="finished" and run["exit_code"]==0 and not run["timed_out"]
    log=(folder/"native.log").read_text(errors="replace")
    draws=[dict(zip(("submitted","prepared","pixels_written"),map(int,m))) for m in
           re.findall(r"MSH draw .* submitted=(\d+) prepared=(\d+) pixels_written=(\d+)",log)]
    report["runs"][name]={"run":run,"sampled_draws":draws}
    paths += [p.relative_to(root).as_posix() for p in folder.glob("frames/*.ppm")]
    paths += [p.relative_to(root).as_posix() for p in (folder/"run.json",folder/"native.log")]
for name in paths:report["hashes"][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
(root/"outputs/MODEL-027-summary.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({name:{"elapsed":r["run"]["elapsed_seconds"],"draws":r["sampled_draws"]} for name,r in report["runs"].items()},indent=2))
