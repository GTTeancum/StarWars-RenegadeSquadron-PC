"""Prepare checkpoint 099 tools without rewriting frozen checkpoint 098 evidence."""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
source = (root/'work/capture-coverage098.py').read_text()
source = source.replace("Observed indices 0..17; 18..21 require fresh menu validation",
                        "Observed indices 0..20 in retained menu evidence; 21 requires fresh menu validation")
out = root/'work/capture-coverage099.py'
assert not out.exists()
out.write_text(source)
(root/'outputs/CHECKPOINT-099.md').write_text('''# Checkpoint 099 — additional era and map coverage in progress

Previous turn is progress: checkpoint 098 finalized 14 successful diagnostics, original pixel/hash verification, same-run render-target classification and a verified 1,493-file source snapshot. Goal remains active/incomplete. Latest user pivot keeps matching manual and skips mipmap/filtering work. No new bindings, transforms or upscales are authorized by this continuation.

Native executable and source remain the final 097 build, verified in 098. Next bounded routes target retained but unopened Galactic Civil War archives: Kashyyyk, Mygeeto, Tatooine and Space Kashyyyk; Space Yavin index 21 must be visually checked before gameplay. Exact UMD opens, process termination, original IDs and true 1280x720 renders must confirm results. Menu names or exit 0 alone do not prove gameplay acceptance. All controller steps/replays and original dumps are preserved separately. No guest state injection or asset substitution.
''',encoding='utf-8')
print('Prepared coverage099 and progress checkpoint.')
