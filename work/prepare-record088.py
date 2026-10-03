from pathlib import Path
r=Path(__file__).resolve().parent.parent
s=(r/'work/record-world087.py').read_text().replace('converted087-echo','converted088-echo').replace('WORLD-STAGE-087-PEB','WORLD-STAGE-088-PEB').replace('WORLD-087-state','WORLD-088-state').replace('CONVERTED-PEB-085','CONVERTED-PEB-088')
(r/'work/record-world088.py').write_text(s)
(r/'work/report-ground088.py').write_text((r/'work/report-ground087.py').read_text().replace('TEXTURE-RUNTIME-087','TEXTURE-RUNTIME-088'))
(r/'work/snapshot-source088.py').write_text((r/'work/snapshot-source087.py').read_text().replace('087','088'))
