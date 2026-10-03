"""Record diffuse-override native evidence and reproducible file hashes."""
import hashlib
import json
import re
from pathlib import Path

root=Path(__file__).resolve().parent.parent
run_dir=root/"work/runs/model026-diffuse"
run=json.loads((run_dir/"run.json").read_text())
assert run["state"]=="finished" and run["exit_code"]==0 and not run["timed_out"]
log=(run_dir/"native.log").read_text(errors="replace")
draws=[dict(zip(("submitted","prepared","pixels_written"),map(int,m))) for m in
       re.findall(r"MSH draw .* submitted=(\d+) prepared=(\d+) pixels_written=(\d+)",log)]
assert draws and any(d["pixels_written"]>0 for d in draws)
report={"run":run,"sampled_draws":draws,"hashes":{}}
paths=["work/audit-model026.py","outputs/MODEL-026-override-tests.log",
       "work/project/source/profiles/renegade/host/override_model.cpp",
       "work/project/source/profiles/renegade/host/override_model.hpp",
       "work/project/source/profiles/renegade/tests/override_model.cpp",
       "work/project/source/profiles/vcs/host/ge_renderer.cpp",
       "work/build-windows-native/bin/RenegadeNative.exe",
       "work/model024-geonosis-replay.txt"]
paths += [p.relative_to(root).as_posix() for p in
          (root/"work/mods-model026/models/republic_logo_blue").iterdir() if p.is_file()]
paths += [p.relative_to(root).as_posix() for p in run_dir.glob("frames/*.ppm")]
paths += [p.relative_to(root).as_posix() for p in (run_dir/"run.json",run_dir/"native.log")]
for name in paths:report["hashes"][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
(root/"outputs/MODEL-026-summary.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"run_exit":run["exit_code"],"elapsed":run["elapsed_seconds"],"draws":draws},indent=2))
