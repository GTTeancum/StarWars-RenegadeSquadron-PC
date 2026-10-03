"""Prepare final capture recording without relabeling earlier run evidence."""
from pathlib import Path
r=Path(__file__).resolve().parent.parent
s=(r/'work/record-world085.py').read_text()
s=s.replace("['coverage085-echo','converted085-echo']","['coverage085-echo','converted087-echo']")
s=s.replace('WORLD-STAGE-085-PEB','WORLD-STAGE-087-PEB').replace('WORLD-085-state','WORLD-087-state').replace("runs['converted085-echo']","runs['converted087-echo']")
(r/'work/record-world087.py').write_text(s)
(r/'work/report-ground087.py').write_text((r/'work/report-ground085.py').read_text().replace('TEXTURE-RUNTIME-085','TEXTURE-RUNTIME-087'))
(r/'work/snapshot-source087.py').write_text((r/'work/snapshot-source086.py').read_text().replace('086','087'))
