import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
import patch_asset_hooks as patch

class AssetHooks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        for unit,(_,hooks) in patch.HOOKS.items():
            text="// Unrelated generated code stays intact\n"+"".join(anchor+"\n"+patch.GUARDS[anchor] for anchor,_ in hooks)
            (self.root/f"generated_unit_{unit}.cpp").write_text(text)
    def tearDown(self):self.temp.cleanup()
    def snapshot(self):return {p.name:p.read_bytes() for p in self.root.iterdir()}
    def run_tool(self,*args):
        return subprocess.run([sys.executable,patch.__file__,str(self.root),*args],capture_output=True)
    def test_install_and_idempotence(self):
        self.assertEqual(self.run_tool().returncode,0)
        before=self.snapshot()
        self.assertEqual(self.run_tool('--check').returncode,0)
        self.assertEqual(self.run_tool().returncode,0)
        self.assertEqual(before,self.snapshot())
    def test_check_never_writes(self):
        before=self.snapshot()
        self.assertNotEqual(self.run_tool('--check').returncode,0)
        self.assertEqual(before,self.snapshot())
    def test_late_invalid_unit_does_not_partially_patch(self):
        path=self.root/'generated_unit_0121.cpp';path.write_text('wrong output\n')
        before=self.snapshot()
        self.assertNotEqual(self.run_tool().returncode,0)
        self.assertEqual(before,self.snapshot())
    def test_duplicate_label(self):
        path=self.root/'generated_unit_0019.cpp';path.write_text(path.read_text()+'L_0882BA6C:\n')
        self.assertNotEqual(self.run_tool().returncode,0)
    def test_moved_call(self):
        path=self.root/'generated_unit_0019.cpp'
        path.write_text(path.read_text()+'renegade::render_trace024::name(rt, ctx);\n')
        self.assertNotEqual(self.run_tool().returncode,0)
    def test_instruction_guard(self):
        path=self.root/'generated_unit_0019.cpp';path.write_text(path.read_text().replace('ctx.gpr[8]','ctx.gpr[9]'))
        self.assertNotEqual(self.run_tool().returncode,0)
    def test_missing_include_repaired(self):
        self.assertEqual(self.run_tool().returncode,0)
        path=self.root/'generated_unit_0019.cpp'
        path.write_text(path.read_text().replace('#include "../host/render_resource_trace024.hpp"\n',''))
        self.assertEqual(self.run_tool().returncode,0)
        self.assertIn('#include "../host/render_resource_trace024.hpp"',path.read_text())
    def test_crlf_preserved(self):
        for path in self.root.iterdir():path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
        self.assertEqual(self.run_tool().returncode,0)
        for path in self.root.iterdir():
            data=path.read_bytes();self.assertEqual(data.count(b'\n'),data.count(b'\r\n'))
    def test_duplicate_include_rejected(self):
        self.assertEqual(self.run_tool().returncode,0)
        path=self.root/'generated_unit_0019.cpp'
        path.write_text('#include "../host/render_resource_trace024.hpp"\n'+path.read_text())
        self.assertNotEqual(self.run_tool().returncode,0)

if __name__=='__main__':unittest.main()
