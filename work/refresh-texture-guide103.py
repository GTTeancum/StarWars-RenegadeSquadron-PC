"""Refresh root entry points after a verified terminal catalog generation."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
c=json.loads((root/'work/texture-catalog103/catalog.json').read_text())['counts']
m=json.loads((root/'outputs/TEXTURE-MUTABILITY-103.json').read_text())
p=root/'Browse-Textures.cmd';s=p.read_text();assert 'texture-catalog102' in s
p.write_text(s.replace('texture-catalog102','texture-catalog103').replace('catalog-textures102','catalog-textures103').replace('build-texture-browser102','build-texture-browser103'))
p=root/'TEXTURE-MATCHING.md';s=p.read_text();assert '4,119 original content IDs' in s
s=s.replace('texture-catalog102','texture-catalog103').replace('catalog-textures102','catalog-textures103').replace('audit-runtime-textures102','audit-runtime-textures103').replace('build-texture-browser102','build-texture-browser103')
s=s.replace('4,119 original content IDs',f"{c['catalog_unique_ids']:,} original content IDs")
s=s.replace('1,553 originals were sampled',f"{c['render_target_sample_ids']:,} originals were sampled")
s=s.replace('143 source-configuration cases',f"{m['case_count']} source-configuration cases")
s=s.replace('108 IDs whose origin',f"{m['unresolved_origin_ids_in_cases']} IDs whose origin")
s=s.replace('total environment opens are 35/47',f"total environment opens are {c['env_archives_opened']}/47")
s=s.replace('Checkpoint 102 records seven new map/era spawn captures and the Geonosis era-menu probe.','Checkpoint 103 records eight completed menu/GC probes, including the upgrade/commander panel. Both GC resource archives are opened. The bounded legacy campaign attempt timed out without outcome captures; it does not prove victory or modern-control acceptance.')
p.write_text(s)
p=root/'TODO.md';s=p.read_text();old='Checkpoint 102 brings coverage to 35/47 ENVS archive\n  paths, including all 34 ordinary Classic/Prequel paths, in retained successful\n  runs. Full traversal, combat and player-controlled flight remain unverified;\n  ten Campaign paths and Galactic Conquest resources remain without runtime opens.'
assert old in s
s=s.replace(old,f"Checkpoint 103 brings coverage to {c['env_archives_opened']}/47 ENVS archive\n  paths, including all 34 ordinary Classic/Prequel paths and both Galactic\n  Conquest resources, in retained successful runs. Full traversal, combat and\n  player-controlled flight remain unverified; ten Campaign paths remain unopened.")
s+='\n- [ ] Diagnose the bounded historical campaign replay before another long attempt.\n  Checkpoint 103 hit its 2400-second limit without outcome frames or a native\n  diagnostic stop/error. Preserve earlier and more frequent native reference\n  frames and use shorter normal-controller stages; final state/last vblank,\n  victory, modern first-mission controls and save/reload remain unknown.\n'
p.write_text(s)
print(json.dumps({'catalog_ids':c['catalog_unique_ids'],'env_opens':c['env_archives_opened'],'guide':'updated','mipmap_filter_changes':False},indent=2))
