"""Inventory and extract only image source files from the user's local 7z archives."""
import hashlib,json,subprocess
from pathlib import Path,PureWindowsPath
root=Path(__file__).resolve().parent.parent
seven=Path('C:/Program Files/7-Zip/7z.exe')
dest=root/'work/texture-sources058';dest.mkdir(exist_ok=True)
report_path=root/'outputs/TEXTURE-SOURCES-058.json'
report={'archives':[]}
for archive in sorted((root/'SWBF2 PSP mod maps').glob('*.7z')):
    sha=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
    listing=subprocess.run([str(seven),'l','-slt','-sccUTF-8',str(archive)],capture_output=True,encoding='utf-8',check=True).stdout
    records=[]
    for block in listing.split('----------',1)[1].strip().split('\n\n'):
        fields=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
        if 'Path' not in fields:continue
        p=PureWindowsPath(fields['Path'])
        if p.is_absolute() or p.drive or '..' in p.parts or ':' in fields['Path'] or 'Symbolic Link' in fields or 'Hard Link' in fields:raise ValueError('Unsafe archive entry')
        if p.suffix.lower() in ('.tga','.dds','.png','.bmp','.jpg','.jpeg'):
            records.append({'path':fields['Path'],'bytes':int(fields['Size']),'crc':fields.get('CRC')})
    target=dest/archive.stem
    if target.exists():raise ValueError(f'Existing output: {target}; inspect before resuming')
    target.mkdir()
    result=subprocess.run([str(seven),'x',str(archive),'-o'+str(target),'-y','-bsp0',*[f'-ir!*{ext}' for ext in ('.tga','.dds','.png','.bmp','.jpg','.jpeg')]],capture_output=True,text=True)
    row={'archive':str(archive.relative_to(root)),'sha256':sha,'bytes':archive.stat().st_size,'image_count':len(records),'image_bytes':sum(x['bytes'] for x in records),'extraction_exit':result.returncode,'images':records}
    if result.returncode:row['error']=result.stdout+result.stderr
    else:
        for record in records:
            p=target/Path(record['path'].replace('\\','/'))
            assert p.is_file() and p.stat().st_size==record['bytes'],p
            record['sha256']=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
    report['archives'].append(row);report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(f'{archive.name}: {len(records)} images, extraction exit {result.returncode}',flush=True)
    if result.returncode:raise SystemExit(result.returncode)
