#include "override_msh.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <fstream>
#include <map>
#include <set>
#include <stdexcept>
#include <string_view>

namespace renegade::overrides {
namespace {
void need(bool ok, const char* reason) { if(!ok) throw std::runtime_error(reason); }
struct Reader {
    std::span<const std::uint8_t> bytes;
    std::span<const std::uint8_t> take(std::size_t count) {
        need(count<=bytes.size(),"Truncated MSH chunk");
        auto value=bytes.first(count);bytes=bytes.subspan(count);return value;
    }
    std::uint32_t u32() { auto b=take(4);return b[0]|(std::uint32_t(b[1])<<8)|(std::uint32_t(b[2])<<16)|(std::uint32_t(b[3])<<24); }
    std::uint16_t u16() { auto b=take(2);return b[0]|(std::uint16_t(b[1])<<8); }
    float f32() { float f=std::bit_cast<float>(u32());need(std::isfinite(f),"Nonfinite MSH value");return f; }
    std::string string() {
        auto end=std::find(bytes.begin(),bytes.end(),0);
        need(end!=bytes.end()&&end-bytes.begin()<=4096,"Invalid MSH string");
        return std::string(bytes.begin(),end);
    }
    std::uint32_t count(std::size_t stride) {
        auto n=u32();need(n<=1000000&&n<=bytes.size()/stride,"Invalid MSH element count");return n;
    }
};
template<class F> void chunks(Reader reader,F action) {
    while(!reader.bytes.empty()) {
        auto tag=reader.take(4);auto size=reader.u32();
        action(std::string_view(reinterpret_cast<const char*>(tag.data()),4),Reader{reader.take(size)});
    }
}
template<std::size_t N> auto vectors(Reader r) {
    std::vector<std::array<float,N>> values(r.count(N*4));
    for(auto& v:values) for(auto& x:v) x=r.f32();
    return values;
}
MshMaterial material(Reader r) {
    MshMaterial out;std::set<std::string> seen;
    chunks(r,[&](auto tag,Reader c) {
        const bool texture=tag[0]=='T'&&tag[1]=='X'&&tag[2]>='0'&&tag[2]<='3'&&tag[3]=='D';
        if(tag=="NAME"||tag=="ATRB"||tag=="DATA"||texture)
            need(seen.insert(std::string(tag)).second,"Duplicate MSH material chunk");
        if(tag=="NAME") out.name=c.string();
        else if(tag=="DATA") {
            need(c.bytes.size()==52,"Invalid MSH material DATA size");
            for(auto* color:{&out.diffuse,&out.specular,&out.ambient})for(auto& v:*color)v=c.f32();
            out.specular_exponent=c.f32();out.has_data=true;
        }
        else if(tag=="ATRB") {need(c.bytes.size()==4,"Invalid MSH material ATRB size");auto b=c.take(4);std::copy(b.begin(),b.end(),out.attributes.begin());}
        else if(tag[0]=='T'&&tag[1]=='X'&&tag[2]>='0'&&tag[2]<='3'&&tag[3]=='D')
            out.textures[tag[2]-'0']=c.bytes.empty()?std::string{}:c.string();
    });return out;
}
MshSegment segment(Reader r,MshScene& scene) {
    MshSegment out;std::vector<std::uint16_t> strips;
    std::uint32_t constant_color=0;bool has_constant=false;
    std::set<std::string> seen;
    chunks(r,[&](auto tag,Reader c) {
        need(seen.insert(std::string(tag)).second,"Duplicate MSH segment chunk");
        if(tag=="MATI") out.material=c.u32();
        else if(tag=="POSL") out.positions=vectors<3>(c);
        else if(tag=="NRML") out.normals=vectors<3>(c);
        else if(tag=="UV0L") out.uv=vectors<2>(c);
        else if(tag=="CLRB") {constant_color=c.u32();has_constant=true;}
        else if(tag=="CLRL") {out.colors.resize(c.count(4));for(auto& v:out.colors)v=c.u32();}
        else if(tag=="WGHT") {
            out.weights.resize(c.count(32));
            for(auto& vertex:out.weights) for(auto& w:vertex) {
                w.bone=c.u32();w.weight=c.f32();need(w.weight>=0&&w.weight<=1,"Invalid MSH weight");
            }
        } else if(tag=="NDXT") {
            out.triangles.resize(c.count(6));for(auto& tri:out.triangles)for(auto& v:tri)v=c.u16();
        } else if(tag=="STRP") {strips.resize(c.count(2));for(auto& v:strips)v=c.u16();}
        else if(tag=="SHDW") scene.has_shadow_volumes=true;
    });
    // NDXT and STRP can describe the same geometry; never emit both.
    if(out.triangles.empty()&&!strips.empty()) {
        std::size_t start=0;
        while(start<strips.size()) {
            need(start+2<strips.size()&&(strips[start]&0x8000)&&(strips[start+1]&0x8000),"Invalid MSH strip start");
            std::size_t end=start+2;
            while(end<strips.size()&&!(strips[end]&0x8000))++end;
            for(std::size_t i=start+2;i<end;++i) {
                std::uint32_t a=strips[i-2]&0x7fff,b=strips[i-1]&0x7fff,c=strips[i];
                if((i-start)&1)std::swap(a,b);
                if(a!=b&&b!=c&&a!=c)out.triangles.push_back({a,b,c});
            }
            need(end>=start+3,"Empty MSH triangle strip");start=end;
        }
    }
    auto n=out.positions.size();
    need(out.normals.empty()||out.normals.size()==n,"MSH normal count mismatch");
    need(out.uv.empty()||out.uv.size()==n,"MSH UV count mismatch");
    need(out.weights.empty()||out.weights.size()==n,"MSH weight count mismatch");
    if(has_constant&&out.colors.empty())out.colors.assign(n,constant_color);
    need(out.colors.empty()||out.colors.size()==n,"MSH color count mismatch");
    for(auto tri:out.triangles)for(auto i:tri)need(i<n,"MSH triangle index out of range");
    return out;
}
MshNode node(Reader r,MshScene& scene) {
    MshNode out;std::set<std::string> seen;
    chunks(r,[&](auto tag,Reader c) {
        need(seen.insert(std::string(tag)).second,"Duplicate MSH model chunk");
        if(tag=="NAME")out.name=c.string();
        else if(tag=="PRNT")out.parent=c.string();
        else if(tag=="MNDX")out.index=c.u32();
        else if(tag=="MTYP")out.type=c.u32();
        else if(tag=="FLGS")out.flags=c.u32();
        else if(tag=="TRAN") {
            for(auto& v:out.scale)v=c.f32();for(auto& v:out.rotation)v=c.f32();for(auto& v:out.translation)v=c.f32();
            float length=0;for(auto v:out.rotation)length+=v*v;
            need(std::isfinite(length)&&length>1e-12f,"Invalid MSH quaternion");
            for(auto& v:out.rotation)v/=std::sqrt(length);
        } else if(tag=="GEOM") chunks(c,[&](auto t,Reader g) {
            if(t=="SEGM") {need(out.segments.size()<4096,"Too many MSH segments");out.segments.push_back(segment(g,scene));}
            else if(t=="ENVL") {out.envelope.resize(g.count(4));for(auto& v:out.envelope)v=g.u32();}
            else if(t=="CLTH")scene.has_cloth=true;
        });
    });
    need(!out.name.empty()&&out.index!=0,"Missing MSH model name or index");
    if(out.type==2)scene.has_cloth=true;if(out.type==6)scene.has_shadow_volumes=true;
    return out;
}
void validate(const MshScene& scene) {
    std::map<std::string,std::size_t> names;std::set<std::uint32_t> indices;
    for(std::size_t i=0;i<scene.nodes.size();++i) {
        const auto& n=scene.nodes[i];
        need(names.emplace(n.name,i).second&&indices.insert(n.index).second,"Duplicate MSH model identity");
    }
    for(const auto& n:scene.nodes) {
        auto parent=n.parent;std::set<std::string> chain{n.name};
        while(!parent.empty()) {
            need(chain.insert(parent).second,"Cyclic MSH hierarchy");
            auto it=names.find(parent);need(it!=names.end(),"Missing MSH parent");parent=scene.nodes[it->second].parent;
        }
        for(auto bone:n.envelope)need(indices.contains(bone),"Missing MSH envelope model");
        for(const auto& s:n.segments) {
            need(s.triangles.empty()||s.material<scene.materials.size(),"Invalid MSH material index");
            for(const auto& weights:s.weights)for(auto w:weights)if(w.weight>0)
                need(n.envelope.empty()?indices.contains(w.bone):w.bone<n.envelope.size(),"Invalid MSH bone index");
        }
    }
}
}
bool parse_msh(std::span<const std::uint8_t> bytes,MshScene& output,std::string& error) {
    try {
        need(bytes.size()<=128u*1024u*1024u,"MSH exceeds 128 MiB limit");
        Reader r{bytes};auto tag=r.take(4);
        need(std::string_view(reinterpret_cast<const char*>(tag.data()),4)=="HEDR","Expected classic Battlefront HEDR");
        auto size=r.u32();need(size==r.bytes.size(),"Invalid MSH root size");
        MshScene scene;bool found=false;
        chunks(r,[&](auto t,Reader c) {
            if(t=="MSH2") {
                need(!found,"Duplicate MSH2");found=true;bool materials=false;
                chunks(c,[&](auto id,Reader payload) {
                    if(id=="MATL") {
                        need(!materials,"Duplicate MATL");materials=true;auto count=payload.u32();need(count<=4096,"Too many MSH materials");
                        chunks(payload,[&](auto mt,Reader m){need(mt=="MATD"&&scene.materials.size()<count,"Invalid MATL contents");scene.materials.push_back(material(m));});
                        need(scene.materials.size()==count,"MSH material count mismatch");
                    } else if(id=="MODL") {need(scene.nodes.size()<4096,"Too many MSH models");scene.nodes.push_back(node(payload,scene));}
                });
            } else if(t=="ANM2")scene.has_animation=true;
        });
        need(found&&!scene.nodes.empty(),"MSH2 has no models");validate(scene);
        output=std::move(scene);error.clear();return true;
    }catch(const std::exception& ex){error=ex.what();return false;}
}
bool load_msh(const std::filesystem::path& path,MshScene& output,std::string& error) {
    try {
        std::ifstream f(path,std::ios::binary|std::ios::ate);need(bool(f),"Cannot open MSH override");
        auto size=f.tellg();need(size>0&&size<=128*1024*1024,"Invalid MSH file size");
        std::vector<std::uint8_t> bytes(static_cast<std::size_t>(size));f.seekg(0);
        need(bool(f.read(reinterpret_cast<char*>(bytes.data()),size)),"MSH read failed");
        return parse_msh(bytes,output,error);
    }catch(const std::exception& ex){error=ex.what();return false;}
}
}
