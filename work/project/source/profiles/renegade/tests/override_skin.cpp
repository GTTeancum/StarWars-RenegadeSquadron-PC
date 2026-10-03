#include "../host/override_skin.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>
#include <fstream>
#include <chrono>
#include <sstream>
using namespace renegade::overrides;
PoseMatrix identity(){return {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};}
MshScene fixture(){
    MshScene s;s.materials.resize(1);
    MshNode root;root.name="root";root.index=10;root.translation={2,0,0};
    MshNode a;a.name="a";a.index=20;a.parent="root";a.translation={1,0,0};
    MshNode b;b.name="b";b.index=30;b.parent="root";b.translation={-1,0,0};
    MshNode mesh;mesh.name="mesh";mesh.index=40;mesh.parent="root";mesh.envelope={30,20};
    MshSegment segment;segment.positions={{0,0,0},{1,0,0},{0,1,0}};
    segment.normals={{1,1,0},{1,1,0},{1,1,0}};segment.uv={{0.2f,0.3f},{0,0},{1,1}};
    segment.colors={0xff123456,0xff123456,0xff123456};segment.triangles={{0,1,2}};
    segment.weights.resize(3);for(auto& w:segment.weights){w[0]={0,1};w[1]={1,3};}
    mesh.segments.push_back(segment);s.nodes={root,a,b,mesh};return s;
}
int main(){
    unsigned checks=0;auto check=[&](bool b,const char* why){++checks;if(!b)throw std::runtime_error(why);};
    auto near=[](float a,float b){return std::abs(a-b)<1e-5f;};
    auto directory=std::filesystem::temp_directory_path()/("renegade-skin-test-"+
        std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    struct Cleanup {std::filesystem::path path;~Cleanup(){std::error_code ec;std::filesystem::remove_all(path,ec);}} cleanup{directory};
    try {
        std::filesystem::create_directories(directory);
        auto path=directory/"model.bindings";
        auto save=[&](const std::string& data){std::ofstream file(path,std::ios::binary);file<<data;};
        const std::string matrix="1 0 0 0 0 1 0 0 0 0 1 0 -3 0 0 1";
        const std::string record="20 0 "+matrix;
        std::string binding_error;std::vector<SkinBinding> loaded;
        save("RS_SKIN_BINDINGS 1\r\n1\r\n"+record+"\r\n");
        check(load_skin_bindings(path,loaded,binding_error)&&loaded.size()==1&&
              loaded[0].msh_index==20&&loaded[0].model_to_bone[12]==-3,"Load column-major correction from CRLF text");
        for(const auto& invalid:std::vector<std::string>{
            "RS_SKIN_BINDINGS 2 1 "+record,
            "RS_SKIN_BINDINGS 1 0",
            "RS_SKIN_BINDINGS 1 4097",
            "RS_SKIN_BINDINGS 1 -1",
            "RS_SKIN_BINDINGS 1 1 -20 0 "+matrix,
            "RS_SKIN_BINDINGS 1 1 20 256 "+matrix,
            "RS_SKIN_BINDINGS 1 1 4294967296 0 "+matrix,
            "RS_SKIN_BINDINGS 1 2 "+record+" "+record,
            "RS_SKIN_BINDINGS 1 1 20 0 1 0",
            "RS_SKIN_BINDINGS 1 1 "+record+" trailing",
            "RS_SKIN_BINDINGS 1 1 20 0 nan 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1",
            "RS_SKIN_BINDINGS 1 1 20 0 1 0 0 1 0 1 0 0 0 0 1 0 0 0 0 1",
            "RS_SKIN_BINDINGS 1 1 20 0 0 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1",
            std::string(1024*1024+1,' ')}){
            save(invalid);check(!load_skin_bindings(path,loaded,binding_error)&&loaded.size()==1&&
                loaded[0].model_to_bone[12]==-3&&!binding_error.empty(),"Invalid mapping rejected without changing output");
        }
        check(!load_skin_bindings(directory/"missing",loaded,binding_error),"Missing mapping rejected");
        auto s=fixture();std::array<SkinBinding,2> bindings{{{20,0,identity()},{30,1,identity()}}};
        bindings[0].model_to_bone[12]=-3;bindings[1].model_to_bone[12]=-1;
        SkinModel skin;Model model;std::string error;
        check(compile_skin(s,bindings,skin,error),"Compile weighted hierarchy");
        check(skin.influences[0][0][0].binding==1&&near(skin.influences[0][0][1].weight,0.75f),
              "ENVL indirection and weight normalization");
        check(near(skin.bind_model.segments[0].vertices[0].position[0],2),"Mesh parent applied before skinning");
        PoseSnapshot pose;pose.bones={identity(),identity()};pose.bones[0][12]=3;pose.bones[1][12]=1;
        check(deform_skin(skin,pose,model,error),"Deform bind pose");
        check(near(model.segments[0].vertices[0].position[0],2)&&near(model.segments[0].vertices[2].position[1],1),
              "Bind pose reconstructs original geometry");
        auto image=std::make_shared<Texture>();skin.bind_model.segments[0].texture=image;
        pose.bones[0][12]=7;pose.bones[1][13]=-2;
        check(deform_skin(skin,pose,model,error),"Blend animated two-bone pose");
        auto v=model.segments[0].vertices[0];
        check(near(v.position[0],5)&&near(v.position[1],-0.5f),"Weighted positions match hand calculation");
        check(v.color==0xff123456&&v.uv==std::array<float,2>{0.2f,0.3f}&&model.segments[0].texture==image,
              "Deformation preserves color UV and texture ownership");
        for(auto& w:s.nodes.back().segments[0].weights){w={};w[0]={1,1};}
        check(compile_skin(s,bindings,skin,error),"Compile single-bone influence");
        pose.bones[0]=identity();pose.bones[0][0]=2;pose.bones[0][12]=3;
        check(deform_skin(skin,pose,model,error),"Nonuniform scaled pose");
        v=model.segments[0].vertices[0];
        check(near(v.normal[0],1/std::sqrt(5.f))&&near(v.normal[1],2/std::sqrt(5.f)),
              "Normals use inverse transpose and normalize");
        check(near(v.position[0],1),"Scale acts around converted bone origin");
        pose.bones[0]={0,1,0,0,-1,0,0,0,0,0,1,0,3,0,0,1};
        check(deform_skin(skin,pose,model,error),"Rotate around mapped bone origin");
        v=model.segments[0].vertices[0];
        check(near(v.position[0],3)&&near(v.position[1],-1)&&near(v.normal[0],-1/std::sqrt(2.f)),
              "Joint rotation transforms positions and normals");
        model.source_path="preserve";pose.bones[0]=identity();pose.bones[0][0]=0;
        check(!deform_skin(skin,pose,model,error)&&model.source_path=="preserve","Singular pose preserves output");
        pose.bones.clear();check(!deform_skin(skin,pose,model,error),"Missing pose bone rejected");
        skin.bind_model.source_path="preserve";
        auto bad=bindings;bad[0].model_to_bone[3]=1;
        check(!compile_skin(s,bad,skin,error)&&skin.bind_model.source_path=="preserve","Non-affine binding preserves output");
        s.nodes.back().segments[0].weights[0][0].weight=-1;
        check(!compile_skin(s,bindings,skin,error),"Negative weight rejected");
        s=fixture();s.nodes.back().segments[0].weights[0]={};
        check(!compile_skin(s,bindings,skin,error),"Zero weight sum rejected");
        s=fixture();s.nodes.back().envelope={20,999};
        check(!compile_skin(s,bindings,skin,error),"Unmapped positive influence rejected");
        s=fixture();s.nodes.back().segments[0].weights[0][0].weight=std::numeric_limits<float>::quiet_NaN();
        check(!compile_skin(s,bindings,skin,error),"Nonfinite weight rejected");
        s=fixture();s.nodes.back().envelope.clear();
        for(auto& w:s.nodes.back().segments[0].weights){w[0].bone=30;w[1].bone=20;}
        check(compile_skin(s,bindings,skin,error),"Direct model indices without ENVL supported");
        s.has_animation=true;
        check(compile_skin(s,bindings,skin,error),"External pose adapter accepts unused embedded clips");
        s.has_cloth=true;
        check(!compile_skin(s,bindings,skin,error),"Cloth remains explicitly unsupported");
        s=fixture();check(compile_skin(s,bindings,skin,error),"Compile camera test skin");
        PoseStore store;PoseIdentity id{};auto camera=identity();camera[12]=10;
        auto a=identity(),b=identity();a[12]=3;b[12]=1;
        store.submit(id,2,0,a,camera);auto captured=store.submit(id,2,1,b,camera);
        check(captured&&deform_skin_camera(skin,*captured,model,error),"Deform camera-composed pose");
        check(near(model.segments[0].vertices[0].position[0],12),"Camera translation applied exactly once");
        auto incomplete=*captured;incomplete.worlds.pop_back();model.source_path="preserve";
        check(!deform_skin_camera(skin,incomplete,model,error)&&model.source_path=="preserve","Missing camera data preserves output");
        std::cout<<checks<<" skin checks passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<"After "<<checks<<" checks: "<<e.what()<<'\n';return 1;}
}
