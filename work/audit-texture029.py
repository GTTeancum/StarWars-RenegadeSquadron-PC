"""Compare bounded native startup runs and preserve cache/build evidence."""
import hashlib
import json
import re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
report={"runs":{},"hashes":{}}
paths=["work/audit-texture029.py","outputs/TEXTURE-029-tests.log",
       "work/project/source/profiles/renegade/host/override_source_cache.hpp",
       "work/project/source/profiles/renegade/tests/override_render.cpp",
       "work/project/source/profiles/vcs/host/ge_renderer.cpp",
       "work/build-windows-native/bin/RenegadeNative.exe"]
for name in ("texture029-before","texture029-after","texture029-disabled"):
    folder=root/"work/runs"/name
    run=json.loads((folder/"run.json").read_text())
    assert run["state"]=="finished",f"Still running: {name}"
    log=(folder/"native.log").read_text(errors="replace")
    match=re.search(r"texture source cache hits=(\d+) misses=(\d+)",log)
    result={"run":run,"cache":dict(zip(("hits","misses"),map(int,match.groups()))) if match else None}
    frames=list(folder.glob("frames/*.ppm"))
    result["frames"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in frames}
    report["runs"][name]=result
    paths += [p.relative_to(root).as_posix() for p in (folder/"run.json",folder/"native.log")]
for name in paths:report["hashes"][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
report["all_frames_identical"]=all(r["frames"] and r["frames"]==report["runs"]["texture029-after"]["frames"] for r in report["runs"].values())
(root/"outputs/TEXTURE-029-summary.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"all_frames_identical":report["all_frames_identical"],"runs":{name:{"elapsed":r["run"].get("elapsed_seconds"),"exit":r["run"]["exit_code"],"cache":r["cache"]} for name,r in report["runs"].items()}},indent=2))
