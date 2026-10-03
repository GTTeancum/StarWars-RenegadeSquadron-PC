"""Share the existing validated source-cache resolver between CPU/GPU draws."""
from pathlib import Path
p=Path(__file__).resolve().parent/'project/source/profiles/vcs/host/ge_renderer.cpp'
s=p.read_text()
if 'void bind_override_texture(' in s:raise SystemExit('Shared resolver already applied; no changes.')
start=s.index('#if defined(RENEGADE_MATERIAL_AUDIT009)\n    if (setup.texture_enabled && renegade::overrides::textures_enabled())',s.index('void bind_fragment_buffers'))
end=s.index('\n#endif',start)+len('\n#endif')
block=s[start:end]
body=block.split('\n',1)[1].rsplit('\n#endif',1)[0]
body=body.replace('setup.texture_enabled && renegade::overrides::textures_enabled()','renegade::overrides::textures_enabled()').replace('            auto& t=setup.texture;\n','')
helper='#if defined(RENEGADE_MATERIAL_AUDIT009)\nvoid bind_override_texture(const psprecomp::GuestMemory& memory,TextureSetup& t) noexcept {\n'+body+'\n}\n#endif\n\n'
s=s[:start]+'#if defined(RENEGADE_MATERIAL_AUDIT009)\n    if(setup.texture_enabled)bind_override_texture(memory,setup.texture);\n#endif'+s[end:]
at=s.index('void bind_fragment_buffers')
s=s[:at]+helper+s[at:]
assert 'auto& t=setup.texture;' not in helper
p.write_text(s)
