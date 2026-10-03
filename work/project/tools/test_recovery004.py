#!/usr/bin/env python3
"""Synthetic accept/reject checks; not game execution or PSP equivalence tests."""
import copy,hashlib,json,tempfile,unittest,zipfile,stat
from pathlib import Path
from verify_aot004 import verify
from verify_checkpoint004 import process
H=lambda b:hashlib.sha256(b).hexdigest()
class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name);self.src=self.r/'source';self.src.mkdir();(self.src/'unit.cpp').write_bytes(b'unit');self.a=self.r/'a.a';self.a.write_bytes(b'synthetic archive');self.b=self.r/'binding.json'
  self.binding={'format':'renegade-aot-binding-v1','compiler':'GNU','version':'14.2.0','target':'x86_64-linux-gnu','archive_sha256':H(self.a.read_bytes()),'files':[{'path':'unit.cpp','sha256':H(b'unit')}]}
 def tearDown(self):self.tmp.cleanup()
 def aot(self,b=None,**kwargs):
  self.b.write_text(json.dumps(self.binding if b is None else b));args={'compiler':'GNU','version':'14.2.0','target':'x86_64-linux-gnu'};args.update(kwargs);return verify(self.src,self.a,self.b,**args)
 def archive(self,changes=None,extra=None,duplicate=False):
  zpath=self.r/'test.zip';m={'format':'renegade-native-checkpoint-v4','files':[{'path':'source/unit.cpp','size':4,'sha256':H(b'unit')},{'path':'empty','size':0,'sha256':H(b'')}]}
  if changes:changes(m)
  with zipfile.ZipFile(zpath,'w') as z:
   z.writestr('manifest.json',json.dumps(m));z.writestr('source/unit.cpp',b'unit');z.writestr('empty',b'')
   if duplicate:z.writestr('empty',b'')
   if extra:z.writestr(*extra)
  return zpath
 def test_aot_valid(self):self.assertEqual(self.aot(),1)
 def test_compiler_version_target(self):
  for k,v in [('compiler','Clang'),('version','13'),('target','windows')]:
   with self.subTest(k=k),self.assertRaises(ValueError):self.aot(**{k:v})
 def test_aot_source_mutation(self):
  (self.src/'unit.cpp').write_bytes(b'Unit')
  with self.assertRaises(ValueError):self.aot()
 def test_aot_archive_mutation(self):
  self.a.write_bytes(b'changed archive')
  with self.assertRaises(ValueError):self.aot()
 def test_aot_format_and_empty(self):
  for k,v in [('format','bad'),('files',[])]:
   b=copy.deepcopy(self.binding);b[k]=v
   with self.subTest(k=k),self.assertRaises(ValueError):self.aot(b)
 def test_aot_traversal_duplicate_bad_hash(self):
  for mutation in ('path','duplicate','hash'):
   b=copy.deepcopy(self.binding)
   if mutation=='path':b['files'][0]['path']='../unit.cpp'
   if mutation=='duplicate':b['files'].append(b['files'][0])
   if mutation=='hash':b['files'][0]['sha256']='invalid'
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.aot(b)
 def test_zip_valid_extract(self):
  z=self.archive();self.assertEqual(process(z),2);self.assertEqual(process(z,self.r/'restored'),2);self.assertEqual((self.r/'restored/source/unit.cpp').read_bytes(),b'unit');self.assertEqual((self.r/'restored/empty').stat().st_size,0)
 def test_zip_bad_digest(self):
  z=self.archive(lambda m:m['files'][0].update(sha256='0'*64))
  with self.assertRaises(ValueError):process(z)
 def test_zip_bad_size(self):
  z=self.archive(lambda m:m['files'][0].update(size=3))
  with self.assertRaises(ValueError):process(z)
 def test_zip_extra_traversal(self):
  for name in ('extra','../escape','/absolute','drive:stream'):
   with self.subTest(name=name),self.assertRaises(ValueError):process(self.archive(extra=(name,b'x')))
 def test_zip_duplicate(self):
  with self.assertRaises(ValueError):process(self.archive(duplicate=True))
 def test_zip_duplicate_manifest(self):
  with self.assertRaises(ValueError):process(self.archive(lambda m:m['files'].append(m['files'][0])))
 def test_zip_no_overwrite(self):
  with self.assertRaises(ValueError):process(self.archive(),self.src)
 def test_zip_failed_extract_removed(self):
  with self.assertRaises(ValueError):process(self.archive(lambda m:m['files'][0].update(sha256='0'*64)),self.r/'broken')
  self.assertFalse((self.r/'broken').exists());self.assertFalse(list(self.r.glob('.renegade-verify-*')))
if __name__=='__main__':unittest.main(verbosity=2)
