from pathlib import Path
import subprocess,sys,struct
# Build-time SPIR-V embedding; the player never needs a shader compiler or SDK.
dxc,source,output=sys.argv[1:]
output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
parts=['#pragma once\n#include <cstdint>\n']
for name,entry,profile in [('vertex','VSMain','vs_6_0'),('pixel','PSMain','ps_6_0')]:
    spv=output.with_suffix('.'+name+'.spv')
    subprocess.run([dxc,'-spirv','-fspv-target-env=vulkan1.1','-fvk-use-dx-layout','-T',profile,'-E',entry,'-Fo',str(spv),source],check=True)
    data=spv.read_bytes(); words=struct.unpack('<'+'I'*(len(data)//4),data)
    parts.append('inline constexpr std::uint32_t vulkan_'+name+'_spirv[]={\n'+','.join(hex(x) for x in words)+'\n};\n')
output.write_text(''.join(parts))
