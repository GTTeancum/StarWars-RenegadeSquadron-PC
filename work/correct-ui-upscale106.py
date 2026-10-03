"""Preserve first candidate; correct proven UI atlas handling in a new pack."""
import copy, hashlib, io, json, shutil
from collections import Counter
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
old_path=root/'outputs/TEXTURE-PACK-106.json';report=copy.deepcopy(json.loads(old_path.read_text()))
folder=root/'work/mods-upscale106-ui2/textures';folder.mkdir(parents=True,exist_ok=True)
corrections=[]
for r in report['files']:
 prior=root/r['replacement'];assert sha(prior)==r['replacement_sha256']
 dest=folder/prior.name
 names=[n.lower().replace('\\','/') for n in r['names']]
 archives=[n.lower().replace('\\','/') for n in r['archives']]
 explicit=any(any(t in n for t in ['/gui/','/fonts/','/hud/','/interface/','/icons/','reticle','minimap','cursor','button','logo']) for n in names)
 dedicated=any(n.rsplit('/',1)[-1] in ['fonts.asr','hud.asr','pspbuttons.asr'] or n.rsplit('/',1)[-1].startswith('hud_weapons') for n in archives)
 named_world=any(any(t in n for t in ['/characters/','/weapons/','/environments/','/objects/','/vehicles/']) for n in names)
 menu_fallback=any(n.startswith('guimenu/') for n in archives) and not named_world
 ui=explicit or dedicated or menu_fallback
 if ui and r['method']=='real_esrnet4x_fidelity_blend':
  data=(root/r['original']).read_bytes();original=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
  corrected=original.resize((original.width*4,original.height*4),Image.Resampling.NEAREST)
  if dest.exists(): assert Image.open(dest).convert('RGBA').tobytes()==corrected.tobytes()
  else: corrected.save(dest)
  corrections.append(dict(id=r['id'],names=r['names'],archives=r['archives'],prior_sha256=r['replacement_sha256'],corrected_sha256=sha(dest),reason='Explicit UI path/dedicated UI archive/menu resource without named world provenance; exact RGBA4x.'))
  r['effective_method']='integer4x_ui_review_correction';r['neural_weight']=0
  r['source_fidelity']=dict(rgb_mae=0.,rgb_p99=0.,max_channel_error=0,mean_channel_shift=[0.,0.,0.])
  r['reasons'].append('Final visual review exposed GUI path delimiter bug; UI2 uses independent normalized provenance paths.')
 else:
  if dest.exists():assert dest.read_bytes()==prior.read_bytes()
  else:shutil.copyfile(prior,dest)
 side=prior.with_suffix('.json')
 if side.exists():
  target=dest.with_suffix('.json')
  if target.exists():assert target.read_bytes()==side.read_bytes()
  else:shutil.copyfile(side,target)
 r['replacement']=dest.relative_to(root).as_posix();r['replacement_sha256']=sha(dest)
report['effective_counts']=dict(Counter(r.get('effective_method',r['method']) for r in report['files']))
report['ui_revision']=dict(prior_manifest_sha256=sha(old_path),corrected_images=len(corrections),corrections=corrections,
 scope='Independent normalized name/archive checks. Named character/weapon/environment/object/vehicle resources in menus remain world art unless explicit UI names establish otherwise. Existing355 authored images stay preferred.')
report['visual_scope']='Final UI correction pending independent audit and new gameplay. First candidate/intermediates retained; no batch rerun.'
p=root/'outputs/TEXTURE-PACK-106-ui2.json'
if p.exists():assert json.loads(p.read_text())==report
else:p.write_text(json.dumps(report,indent=2)+'\n')
(folder.parent/'README.md').write_text('# Fidelity4x corrected pack\n\nExisting355 source overrides preferred and unchanged. UI/typography exact4x; generated alpha exact. World RGB uses limited RealESRNet blend. See outputs/TEXTURE-PACK-106-ui2.json. Replace original content-ID images with your DDS/TGA/PNG; keep one image extension per ID. No channel/rotation transforms.\n',encoding='utf-8')
print(json.dumps(dict(corrected_ui=len(corrections),effective_counts=report['effective_counts']),indent=2))
