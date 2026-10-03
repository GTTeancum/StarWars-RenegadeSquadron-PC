#pragma once
#include "psprecomp/guest_memory.hpp"
#include "psprecomp/common.hpp"
#include <array>
#include <cstdint>
#include <vector>
namespace renegade {
// GE B2/B3/B4/B5, EA/EB/EC/EE: layout cross-checked against PSPSDK sceGuCopyImage.
// Snapshot the full source rectangle so overlapping rectangles do not depend on
// the order of host memcpy calls. Validate all rows before any destination write.
inline std::size_t ge_transfer(psprecomp::GuestMemory& m,const std::array<std::uint32_t,256>& c) {
 const auto s=(c[0xb2]&0xffffffu)|((c[0xb3]&0xff0000u)<<8u);
 const auto d=(c[0xb4]&0xffffffu)|((c[0xb5]&0xff0000u)<<8u);
 const auto sw=c[0xb3]&0x7ffu,dw=c[0xb5]&0x7ffu;
 const auto sx=c[0xeb]&1023u,sy=(c[0xeb]>>10u)&1023u;
 const auto dx=c[0xec]&1023u,dy=(c[0xec]>>10u)&1023u;
 const auto w=(c[0xee]&1023u)+1u,h=((c[0xee]>>10u)&1023u)+1u;
 const std::uint32_t bpp=(c[0xea]&1u)?4u:2u;
 if (!sw || !dw) throw psprecomp::Error("GE image transfer has zero stride");
 std::vector<std::uint32_t> sources(h),destinations(h);
 const auto rowbytes=static_cast<std::size_t>(w)*bpp;
 for(std::uint32_t y=0;y<h;++y){
  const auto sa=std::uint64_t(s)+(std::uint64_t(sy+y)*sw+sx)*bpp;
  const auto da=std::uint64_t(d)+(std::uint64_t(dy+y)*dw+dx)*bpp;
  if(sa>0xffffffffu || da>0xffffffffu || !m.contains(static_cast<std::uint32_t>(sa),rowbytes) || !m.contains(static_cast<std::uint32_t>(da),rowbytes))
   throw psprecomp::Error("GE image transfer rectangle is outside mapped memory");
  sources[y]=static_cast<std::uint32_t>(sa);destinations[y]=static_cast<std::uint32_t>(da);
 }
 std::vector<std::uint8_t> snapshot(rowbytes*h);
 for(std::uint32_t y=0;y<h;++y) for(std::size_t x=0;x<rowbytes;++x) snapshot[y*rowbytes+x]=m.aot_load8(sources[y]+static_cast<std::uint32_t>(x));
 for(std::uint32_t y=0;y<h;++y) for(std::size_t x=0;x<rowbytes;++x) m.aot_store8(destinations[y]+static_cast<std::uint32_t>(x),snapshot[y*rowbytes+x]);
 return snapshot.size();
}
}
