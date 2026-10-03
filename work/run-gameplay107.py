"""Run representative enhanced pack scenarios after independent pack verification."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
assert (root/'outputs/UPSCALER-107-verification.json').exists()
routes=[('mygeeto','clone',0,'mygeeto-clone'),('hoth','gcw',0,'hoth-gcw'),('space-kashyyyk','gcw',0,'space-kashyyyk-gcw'),('geonosis','clone',1,'geonosis-clone-mode1'),('endor','gcw',2,'endor-gcw-mode2')]
for planet,era,mode,label in routes:
 name='textures107-'+label+'-gpu';assert not (root/'work/runs'/name).exists()
 subprocess.run([sys.executable,'work/capture-upscale106.py',planet,'--name',name,'--era',era,'--mode-index',str(mode),'--renderer','gpu','--pack','enhanced107'],cwd=root,check=True)
 subprocess.run([sys.executable,'work/inspect-upscale106.py',name],cwd=root,check=True)
print('Five enhanced gameplay routes captured and inspected')
