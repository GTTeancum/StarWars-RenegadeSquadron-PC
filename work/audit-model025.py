"""Summarize local SWBF2 compatibility diagnostics without copying game assets."""
import collections
import csv
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

report = {"asset_root": "Z:/Modding/SWBF2_Modtools/assets",
          "scope": "sides and worlds MSH files; rigid geometry conversion only, not full material or animation compatibility"}
for label, name in [("before_colors", "MODEL-025-real-assets.tsv"),
                    ("after_colors", "MODEL-025-real-assets-colors.tsv")]:
    path = root / "outputs" / name
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    assert len(rows) == 2738 and all(r["parsed"] in ("0", "1") for r in rows)
    report[label] = {"files": len(rows), "parsed": sum(r["parsed"] == "1" for r in rows),
                     "compiled": sum(r["compiled"] == "1" for r in rows),
                     "failures": dict(collections.Counter(r["error"] for r in rows if r["error"])),
                     "report_sha256": digest(path)}
report["hashes"] = {}
paths = ["work/model025-asset-paths.txt", "work/model024-geonosis-replay.txt",
         "work/audit-model025.py", "outputs/MODEL-025-ctest.log",
         "outputs/MODEL-025-frame-comparison.json",
         "work/mods-model025/models/republic_logo_blue/part-0.msh",
         "work/build-windows-native/bin/RenegadeNative.exe"]
paths += [p.relative_to(root).as_posix() for p in (root / "work/project/source/profiles/renegade/host").glob("override_*")]
paths += ["work/project/source/profiles/vcs/host/ge_renderer.cpp",
          "work/project/source/profiles/renegade/host/render_resource_trace024.hpp",
          "work/project/source/profiles/renegade/tests/override_model.cpp",
          "work/project/source/profiles/renegade/tests/override_asset_audit.cpp",
          "work/project/source/profiles/renegade/CMakeLists.txt"]
for name in paths:
    report["hashes"][name] = digest(root / name)
for name in ("model025-r2d2", "model025-baseline"):
    path = root / "work/runs" / name / "run.json"
    if path.exists():
        run = json.loads(path.read_text())
        report[name] = run
        report["hashes"][path.relative_to(root).as_posix()] = digest(path)
        for frame in path.parent.glob("frames/*.ppm"):
            report["hashes"][frame.relative_to(root).as_posix()] = digest(frame)
(root / "outputs/MODEL-025-summary.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps({k: report[k] for k in ("before_colors", "after_colors")}, indent=2))
