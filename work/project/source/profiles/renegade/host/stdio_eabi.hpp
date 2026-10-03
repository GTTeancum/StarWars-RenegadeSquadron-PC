#pragma once
#include "psprecomp/runtime.hpp"
#include <cstdio>
#include <cctype>
#include <string>
#include <algorithm>
#include <bit>
namespace renegade {
inline std::string format_psp_printf(psprecomp::Runtime& rt,psprecomp::AllegrexContext& c) {
 auto& m=rt.memory();const auto fmt=m.read_c_string(c.gpr[4],4096);unsigned arg=1;
 auto word=[&](){if(arg<8)return c.gpr[4+arg++];const auto address=std::uint64_t(c.gpr[29])+4*(arg++-8);if(address>0xffffffff || !m.contains(static_cast<std::uint32_t>(address),4))throw psprecomp::Error("printf argument outside PSP stack");return m.load32(static_cast<std::uint32_t>(address));};
 auto wide=[&](){if(arg&1)++arg;const std::uint64_t lo=word();return lo|(std::uint64_t(word())<<32);};
 std::string out;
 for(std::size_t i=0;i<fmt.size();++i){
  if(fmt[i]!='%'){out+=fmt[i];continue;}if(++i==fmt.size())throw psprecomp::Error("Truncated PSP printf format");if(fmt[i]=='%'){out+='%';continue;}
  std::string flags;while(i<fmt.size() && std::string("-+ #0").find(fmt[i])!=std::string::npos)flags+=fmt[i++];
  int width=0,precision=-1;
  if(i<fmt.size() && fmt[i]=='*'){width=static_cast<std::int32_t>(word());++i;if(width<0){flags+='-';width=width==INT32_MIN?1025:-width;}}
  else while(i<fmt.size() && std::isdigit(static_cast<unsigned char>(fmt[i]))){width=width*10+(fmt[i++]-'0');if(width>1024)throw psprecomp::Error("PSP printf width exceeds bound");}
  if(i<fmt.size() && fmt[i]=='.'){++i;precision=0;if(i<fmt.size() && fmt[i]=='*'){precision=static_cast<std::int32_t>(word());++i;}else while(i<fmt.size() && std::isdigit(static_cast<unsigned char>(fmt[i]))){precision=precision*10+(fmt[i++]-'0');if(precision>1024)throw psprecomp::Error("PSP printf precision exceeds bound");}}
  if(width>1024 || precision>1024)throw psprecomp::Error("PSP printf field too large");
  std::string length;while(i<fmt.size() && std::string("hljztL").find(fmt[i])!=std::string::npos)length+=fmt[i++];
  if(i>=fmt.size())throw psprecomp::Error("Missing PSP printf conversion");char conv=fmt[i];std::string spec="%"+flags+(width?std::to_string(width):"")+(precision>=0?"."+std::to_string(precision):"");
  char buffer[8192];int n=-1;
  if(std::string("diuoxX").find(conv)!=std::string::npos){bool iswide=length=="ll"||length=="j";auto v=iswide?wide():std::uint64_t(word());
   if(conv=='d'||conv=='i'){std::int64_t sv=iswide?static_cast<std::int64_t>(v):static_cast<std::int32_t>(v);if(length=="h")sv=static_cast<std::int16_t>(sv);if(length=="hh")sv=static_cast<std::int8_t>(sv);n=std::snprintf(buffer,sizeof(buffer),(spec+"ll"+conv).c_str(),static_cast<long long>(sv));}
   else{if(length=="h")v&=65535;if(length=="hh")v&=255;n=std::snprintf(buffer,sizeof(buffer),(spec+"ll"+conv).c_str(),static_cast<unsigned long long>(v));}}
  else if(conv=='s'){auto ptr=word();std::string value;if(!ptr)value="(null)";else{const auto limit=precision>=0?static_cast<unsigned>(precision):4096u;for(unsigned j=0;j<limit;++j){if(!m.contains(ptr+j,1))throw psprecomp::Error("printf string outside PSP memory");char ch=static_cast<char>(m.load8(ptr+j));if(!ch)break;value+=ch;if(j+1==limit && precision<0)throw psprecomp::Error("Unterminated PSP printf string");}}n=std::snprintf(buffer,sizeof(buffer),(spec+"s").c_str(),value.c_str());}
  else if(conv=='c')n=std::snprintf(buffer,sizeof(buffer),(spec+"c").c_str(),static_cast<int>(word()&255));
  else if(conv=='p')n=std::snprintf(buffer,sizeof(buffer),"0x%08x",word());
  else if(std::string("fFeEgGaA").find(conv)!=std::string::npos)n=std::snprintf(buffer,sizeof(buffer),(spec+conv).c_str(),std::bit_cast<double>(wide()));
  else if(conv=='n'){const auto ptr=word();unsigned size=length=="hh"?1:length=="h"?2:length=="ll"?8:4;if(!m.contains(ptr,size))throw psprecomp::Error("printf count output outside PSP memory");auto count=std::uint64_t(out.size());for(unsigned b=0;b<size;++b)m.store8(ptr+b,static_cast<std::uint8_t>(count>>(8*b)));n=0;}
  else throw psprecomp::Error("Unsupported PSP printf conversion");
  if(n<0 || n>=static_cast<int>(sizeof(buffer)))throw psprecomp::Error("PSP printf formatting overflow");out.append(buffer,static_cast<std::size_t>(n));if(out.size()>65536)throw psprecomp::Error("PSP printf output exceeds bound");
 }
 return out;
}
}
