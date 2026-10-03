from pathlib import Path
r=Path(__file__).resolve().parent.parent
s=(r/'work/analyze-world085.py').read_text().replace('world-analysis085','world-analysis088').replace('CONVERTED-PEB-085','CONVERTED-PEB-088').replace('WORLD-DRAWS-085','WORLD-DRAWS-088')
(r/'work/analyze-world088.py').write_text(s)
s=(r/'work/align-triangles085.py').read_text().replace('world-analysis085','world-analysis088').replace('WORLD-TRIANGLE-ALIGN-085','WORLD-TRIANGLE-ALIGN-088')
s=s.replace("glob('*.msh.json')","glob('hoth_bldg*.msh.json')")
(r/'work/align-triangles088.py').write_text(s)
