"""Check actual decoded pixel identities, including channel order, without altering sources."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
r=Path(__file__).resolve().parent.parent
base=r/'work/map-conversions085/data_PEB/Worlds/PEB/msh'
report=[]
for name in ['PSP_0006_0.tga','PSP_0008_0.tga']:
 src=np.array(Image.open(base/name).convert('RGBA'));matches=[];nearest=[]
 for p in (r/'work/runs/coverage086-echo/textures').glob('*.tga'):
  im=Image.open(p)
  if im.size!=(src.shape[1],src.shape[0]):continue
  decoded=np.array(im.convert('RGBA'))
  for channel_order,pixels in [('RGB',decoded),('BGR',decoded[:,:,[2,1,0,3]])]:
   error=np.abs(src[:,:,:3].astype(np.int16)-pixels[:,:,:3].astype(np.int16))
   mae=float(error.mean());nearest.append(dict(id=p.stem,channel_order=channel_order,rgb_mean_absolute_error=mae,max_error=int(error.max())))
   if np.array_equal(src[:,:,:3],pixels[:,:,:3]):matches.append(dict(id=p.stem,channel_order=channel_order,rgb_exact=True,rgba_exact=bool(np.array_equal(src,pixels)),decoded_path=p.relative_to(r).as_posix()))
 nearest.sort(key=lambda x:x['rgb_mean_absolute_error'])
 report.append(dict(source=(base/name).relative_to(r).as_posix(),source_sha256=hashlib.sha256((base/name).read_bytes()).hexdigest(),dimensions=[src.shape[1],src.shape[0]],runtime_rgb_identity_matches=matches,nearest_same_size=nearest[:3],scope='Exact decoded RGB/RGBA equality is identity evidence; low average error alone is not accepted as an override binding. Images are read only.'))
(r/'outputs/ATLAS-089-identity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
