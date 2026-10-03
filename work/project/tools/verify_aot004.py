#!/usr/bin/env python3
"""Fail closed when a saved AOT archive does not match its source/ABI binding.
Hashes preserve a recorded local snapshot, not an upstream signing identity.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path, PurePosixPath

def verify(source:Path,archive:Path,binding:Path,compiler:str,version:str,target:str)->int:
    b=json.loads(binding.read_text())
    if b.get('format')!='renegade-aot-binding-v1':raise ValueError('Unknown saved AOT binding format')
    for name,value in [('compiler',compiler),('version',version),('target',target)]:
        if b.get(name)!=value:raise ValueError('Saved AOT '+name+' mismatch; perform full source rebuild')
    def digest(path:Path)->str:
        with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
    if digest(archive)!=b['archive_sha256']:raise ValueError('Saved AOT archive hash mismatch')
    root=source.resolve();seen=set();files=b['files']
    if not isinstance(files,list) or not 1<=len(files)<=10000:raise ValueError('Empty/invalid AOT file binding')
    for f in files:
        name=f['path'];relative=PurePosixPath(name);path=root/name
        if not name or name in seen or relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name or relative.as_posix()!=name or not path.resolve().is_relative_to(root):
            raise ValueError('Unsafe or duplicate AOT binding record')
        if not re.fullmatch('[0-9a-f]{64}',f['sha256']):raise ValueError('Invalid source hash')
        seen.add(name)
        if digest(path)!=f['sha256']:raise ValueError('Source/ABI change requires full AOT rebuild: '+name)
    return len(seen)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('archive',type=Path);p.add_argument('binding',type=Path)
    p.add_argument('compiler');p.add_argument('version');p.add_argument('target');a=p.parse_args()
    try:
        count=verify(a.source,a.archive,a.binding,a.compiler,a.version,a.target)
        print(f'Verified saved AOT archive and {count} generated-source/core-header bindings')
    except (ValueError,KeyError,TypeError,OSError) as e:p.exit(2,str(e)+'\n')
