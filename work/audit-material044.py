"""Compare native DATA decoding with independent byte-level reads of real MSHs."""
import csv,hashlib,json,os,struct,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent.parent
exe=root/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'
env=os.environ.copy();env['PATH']=str(root/'work/windows-sdk/bin')+os.pathsep+env['PATH']
def chunks(b):
    at=0
    while at<len(b):
        tag,n=struct.unpack_from('<4sI',b,at);at+=8
        assert at+n<=len(b)
        yield tag,b[at:at+n];at+=n
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
for name in ['cis_inf_bdroid.msh','cis_inf_bdroid_low1.msh']:
    p=Path('Z:/Modding/SWBF2_Modtools/assets/sides/cis/msh')/name
    native=json.loads(subprocess.check_output([str(exe),'--materials',str(p)],env=env,text=True))
    hedr=list(chunks(p.read_bytes()));assert hedr[0][0]==b'HEDR'
    msh=dict(chunks(hedr[0][1]))[b'MSH2'];matl=dict(chunks(msh))[b'MATL'];decoded=[]
    for tag,b in chunks(matl[4:]):
        assert tag==b'MATD';fields=dict(chunks(b));vals=struct.unpack('<13f',fields[b'DATA'])
        decoded.append(dict(has_data=True,flags=fields[b'ATRB'][0],render_type=fields[b'ATRB'][1],specular=list(vals[4:8]),stored_exponent=vals[12]))
    assert native==decoded
    records.append(dict(path=str(p),sha256=sha(p),materials=native))
rows=list(csv.DictReader((root/'outputs/MATERIAL-044-corpus.tsv').open(encoding='utf-8-sig'),delimiter='\t'))
prior=list(csv.DictReader((root/'outputs/MODEL-025-real-assets-colors.tsv').open(encoding='utf-8-sig'),delimiter='\t'))
assert len(rows)==2738
old={r['path']:r for r in prior}
regressions=[r for r in rows if old[r['path']]['parsed']=='1' and r['parsed']!='1']
assert not regressions,regressions
paths=[Path(__file__),exe,root/'work/build-windows-native/bin/RenegadeNative.exe',root/'outputs/MATERIAL-044-tests.log',root/'outputs/MATERIAL-044-corpus.tsv']
paths += [root/'work/project/source/profiles/renegade'/p for p in ['host/override_msh.hpp','host/override_msh.cpp','tests/override_msh.cpp','tests/override_asset_audit.cpp']]
report=dict(scope='Material DATA parser prerequisite; gloss rendering remains disabled',real_asset_checks=records,corpus_files=len(rows),parsed=sum(r['parsed']=='1' for r in rows),parse_regressions_vs025=len(regressions),sha256={p.relative_to(root).as_posix():sha(p) for p in paths})
(root/'outputs/MATERIAL-044-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))
