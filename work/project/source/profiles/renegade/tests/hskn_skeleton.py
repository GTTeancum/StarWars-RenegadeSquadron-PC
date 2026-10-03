import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('reader', Path(__file__).resolve().parents[1]/'tools/hskn_skeleton.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

def string(value):
    b = value.encode()+b'\0'
    return b+b'\0'*((-len(b))%4)

def fixture():
    b = bytearray(b'HSKN'+struct.pack('<5I',0,8,9,0,2)+string('fixture'))
    b += struct.pack('<2I',0,0)
    b += struct.pack('<14f',0,0,0,0,0,0,1, 1,2,3,0,0,0,1)
    # Odd geometry size deliberately unaligns the second name.
    b += string('root')+struct.pack('<I',3)+b'xyz'
    b += string('child')+struct.pack('<I',0)+struct.pack('<2I',4,7)
    struct.pack_into('<I',b,4,len(b))
    return b

class SkeletonTests(unittest.TestCase):
    def test_unaligned_names_and_pose(self):
        r=reader.parse_skeleton(fixture())
        self.assertEqual(r['bones'][1]['name'],'child')
        self.assertEqual(r['bones'][1]['translation'],[1,2,3])
        self.assertEqual(r['bones'][1]['slot_id'],7)
    def test_every_truncation(self):
        b=fixture()
        for size in range(len(b)):
            with self.assertRaises(ValueError): reader.parse_skeleton(b[:size])
    def test_parent_cycle(self):
        b=fixture();struct.pack_into('<I',b,24+len(string('fixture'))+4,1)
        with self.assertRaises(ValueError): reader.parse_skeleton(b)
    def test_unsupported_flags(self):
        b=fixture();struct.pack_into('<I',b,12,13)
        with self.assertRaises(ValueError): reader.parse_skeleton(b)
    def test_nonfinite_pose(self):
        b=fixture();struct.pack_into('<f',b,24+len(string('fixture'))+8,float('nan'))
        with self.assertRaises(ValueError): reader.parse_skeleton(b)
    def test_bad_rotation(self):
        b=fixture();struct.pack_into('<f',b,24+len(string('fixture'))+8+24,0)
        with self.assertRaises(ValueError): reader.parse_skeleton(b)
    def test_trailer(self):
        b=fixture()+b'1234';struct.pack_into('<I',b,4,len(b))
        with self.assertRaises(ValueError): reader.parse_skeleton(b)
    def test_archive_selection(self):
        self.assertEqual(reader.extract_skeleton(b'Asura   '+fixture(),'fixture')['name'],'fixture')
        for b in (b'Asura   '+fixture()+fixture(), b'Asura   '+fixture()[:-1],
                  b'Asura   '+fixture()+b'junk'):
            with self.assertRaises(ValueError): reader.extract_skeleton(b,'fixture')
        with self.assertRaises(ValueError): reader.extract_skeleton(b'Asura   '+fixture(),'absent')
    def test_parent_rotation_affects_child_bind_pose(self):
        b=fixture()
        pose=24+len(string('fixture'))+8
        struct.pack_into('<4f',b,pose+12,0,0,2**-0.5,2**-0.5)
        child=reader.parse_skeleton(b)['bones'][1]
        for actual,expected in zip(child['bind_translation'],(-2,1,3)):
            self.assertAlmostEqual(actual,expected,places=6)

if __name__=='__main__': unittest.main()
