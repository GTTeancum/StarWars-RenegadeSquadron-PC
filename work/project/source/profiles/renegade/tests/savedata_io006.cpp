#include "savedata_io006.hpp"
#include "guest_savedata_preflight006.hpp"
#include <cstring>
#include <limits>
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <thread>
#include <vector>
namespace fs=std::filesystem;
using renegade::savedata::Blob;
static unsigned checks=0;
static void check(bool v,const char* m){++checks;if(!v)throw std::runtime_error(m);}
static void fail_publish(){throw std::runtime_error("injected pre-publication failure");}
static std::vector<std::uint8_t> bytes(const fs::path& p){std::ifstream f(p,std::ios::binary);f.exceptions(std::ios::badbit);return std::vector<std::uint8_t>(std::istreambuf_iterator<char>(f),{});}
static void put(const fs::path&p,const std::vector<std::uint8_t>&b){std::ofstream f(p,std::ios::binary|std::ios::trunc);f.exceptions(std::ios::failbit|std::ios::badbit);if(!b.empty())f.write(reinterpret_cast<const char*>(b.data()),b.size());f.close();}
int main(){
    auto root=fs::temp_directory_path()/("renegade-save-unit-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directory(root);
    try{
        using namespace renegade::savedata;
        std::string error;
        const auto profile=root/"ULUS10292TEST";
        std::vector<std::uint8_t>a(32,0x11),b(32,0x22),c(32,0x33);
        check(commit(profile,{{"DATA.BIN",a},{"ICON0.PNG",b}},error),"initial commit failed");
        check(bytes(profile/"DATA.BIN")==a,"initial main bytes");
        check(bytes(profile/"ICON0.PNG")==b,"initial icon bytes");
        check(!commit(profile,{{"DATA.BIN",c},{"../ICON0.PNG",b}},error),"unsafe auxiliary accepted");
        check(bytes(profile/"DATA.BIN")==a,"rejected auxiliary modified main");
        check(bytes(profile/"ICON0.PNG")==b,"rejected auxiliary modified icon");
        check(!commit(profile,{{"DATA.BIN",c},{"data.bin",b}},error),"case-duplicate output accepted");
        check(bytes(profile/"DATA.BIN")==a,"duplicate output modified main");
        check(!commit(profile,{{"DATA.BIN",c},{"ICON0.PNG",c}},error,fail_publish),"injected failure succeeded");
        check(bytes(profile/"DATA.BIN")==a,"rollback lost main");
        check(bytes(profile/"ICON0.PNG")==b,"rollback lost icon");
        check(!commit(root/"NEW",{{"DATA.BIN",c}},error,fail_publish),"new injected failure succeeded");
        check(!fs::exists(root/"NEW"),"failed new save published a directory");
        check(commit(profile,{{"DATA.BIN",{}}},error),"zero length commit failed");
        check(fs::file_size(profile/"DATA.BIN")==0,"zero length did not truncate");
        check(bytes(profile/"ICON0.PNG")==b,"omitted auxiliary not preserved");
        put(profile/"EXTRA.DAT",a);
        check(commit(profile,{{"DATA.BIN",c},{"ICON0.PNG",c}},error),"multi-file update failed");
        check(bytes(profile/"DATA.BIN")==c && bytes(profile/"ICON0.PNG")==c,"multi-file contents wrong");
        check(bytes(profile/"EXTRA.DAT")==a,"unrelated regular file not preserved");
        for(const auto&bad:std::vector<std::string>{"",".","..","A/../B","A\\B","A:B","A*B","A?B","A\"B","A<B","A>B","A|B","NAME.","NAME ","CON","con.txt","PRN","AUX","NUL","COM1","com9.dat","LPT1","lpt9.any",std::string(1,char(0x80)),std::string("N\0X",3)}){
            bool rejected=false;try{validate_component(bad);}catch(const std::invalid_argument&){rejected=true;}check(rejected,"unsafe name accepted");
            check(!commit(profile,{{bad,a}},error),"commit accepted unsafe name");
            check(bytes(profile/"DATA.BIN")==c,"unsafe name changed main");
        }
        for(const auto&good:std::vector<std::string>{"DATA.BIN","ICON0.PNG","COM0","COM10","LPT0","NORMAL.DAT","ULUS10292TEST"}){validate_component(good);check(true,"valid name");}
        validate_component("",true);check(true,"optional empty suffix");
        fs::create_directory(profile/"NESTED");
        check(!commit(profile,{{"DATA.BIN",a}},error),"nested directory accepted");
        check(bytes(profile/"DATA.BIN")==c,"nested rejection changed main");fs::remove(profile/"NESTED");
        put(profile/"data.bin",b);
        if(fs::equivalent(profile/"DATA.BIN",profile/"data.bin")) {
            // Case-insensitive volumes cannot contain the two distinct fixture files.
            // Exercise a real alias update instead; the collision fixture remains
            // covered when this same test runs on a case-sensitive volume.
            check(bytes(profile/"DATA.BIN")==b,"case alias did not refer to same file");
            check(commit(profile,{{"DATA.BIN",c}},error),"case alias update failed");
            check(bytes(profile/"data.bin")==c,"case alias update lost main");
            std::cout<<"case-insensitive volume: alias update verified; distinct existing-name collision fixture unavailable\n";
        } else {
            check(!commit(profile,{{"DATA.BIN",a}},error),"existing case collision accepted");
            check(bytes(profile/"DATA.BIN")==c,"case collision changed main");fs::remove(profile/"data.bin");
        }
        check(!commit(profile,{{"DATA.BIN",a},{"data.bin",b}},error),"requested case collision accepted");
        check(bytes(profile/"DATA.BIN")==c,"requested case collision changed main");
        const auto external=root/"EXTERNAL.DAT";put(external,a);
        fs::create_symlink(external,profile/"LINK.DAT");
        check(!commit(profile,{{"DATA.BIN",a}},error),"existing symlink accepted");
        check(bytes(external)==a,"symlink referent changed");fs::remove(profile/"LINK.DAT");
        fs::create_directory_symlink(profile,root/"LINKPROFILE");
        check(!commit(root/"LINKPROFILE",{{"DATA.BIN",a}},error),"profile symlink accepted");
        check(bytes(profile/"DATA.BIN")==c,"profile symlink changed real profile");fs::remove(root/"LINKPROFILE");
        put(root/"BLOCKED",a);
        check(!commit(root/"BLOCKED"/"SAVE",{{"DATA.BIN",a}},error),"non-directory root accepted");
        check(bytes(root/"BLOCKED")==a,"blocked root bytes changed");
        check(!commit(profile,{},error),"empty transaction accepted");
        std::vector<Blob> too_many;for(unsigned i=0;i<6;++i)too_many.push_back({"F"+std::to_string(i),a});
        check(!commit(profile,too_many,error),"more than five requested files accepted");
        bool escaped=false;try{validate_paths(root,profile,root/"OUTSIDE.BIN");}catch(const std::invalid_argument&){escaped=true;}check(escaped,"escaped data path accepted");
        // Guest preflight and host staging bridge with owned synthetic memory.
        // This is NOT the production PSP ABI decoder or Runtime implementation.
        constexpr std::uint32_t base=0x08800000u;
        std::array<std::uint8_t,1024> ram{};
        for(std::size_t i=0;i<ram.size();++i) ram[i]=static_cast<std::uint8_t>(i);
        auto contains=[&](std::uint32_t address,std::uint32_t size){return address>=base && std::uint64_t(address)+size<=std::uint64_t(base)+ram.size();};
        unsigned reads=0;
        auto copy_guest=[&](std::uint32_t address,std::uint8_t* out,std::uint32_t size){++reads;if(!contains(address,size))throw std::runtime_error("invalid synthetic read");std::memcpy(out,ram.data()+(address-base),size);};
        const std::array<std::string,5> names{"DATA.BIN","ICON0.PNG","ICON1.PMF","PIC1.PNG","SND0.AT3"};
        std::array<GuestBuffer,5> good{};
        good[0]={base+16,64,32};
        for(unsigned i=1;i<5;++i)good[i]={base+128+i*64,32,16};
        for(unsigned index=0;index<5;++index)for(unsigned kind=0;kind<5;++kind){
            auto bad=good;
            if(kind==0)bad[index].address=0;
            if(kind==1)bad[index].size=bad[index].capacity+1;
            if(kind==2)bad[index].address=base+1020;
            if(kind==3)bad[index].address=0xfffffff8u;
            if(kind==4)bad[index].address=base-32;
            reads=0;bool rejected=false;
            try{auto owned=collect_save_buffers(bad,names,false,contains,copy_guest);(void)owned;}catch(const std::invalid_argument&){rejected=true;}
            check(rejected,"invalid guest range was accepted");
            check(reads==0,"guest copied before all auxiliary buffers validated");
            check(bytes(profile/"DATA.BIN")==c,"invalid preflight changed existing profile");
        }
        reads=0;
        auto owned=collect_save_buffers(good,names,false,contains,copy_guest);
        check(reads==5 && owned.size()==5,"valid guest buffers were not copied once each");
        check(commit(profile,owned,error),"validated synthetic guest transaction failed");
        check(bytes(profile/"DATA.BIN")==std::vector<std::uint8_t>(ram.begin()+16,ram.begin()+48),"guest main round trip mismatch");
        // The raw-data path intentionally ignores every auxiliary descriptor.
        auto raw=good;for(unsigned i=1;i<5;++i)raw[i]={0,0,0xffffffffu};reads=0;
        auto raw_owned=collect_save_buffers(raw,names,true,contains,copy_guest);
        check(reads==1 && raw_owned.size()==1,"raw write did not ignore auxiliary metadata");
        // Empty main remains an explicit blob; empty auxiliaries are omitted.
        auto empty=good;for(auto&b:empty)b={0,0,0};reads=0;
        auto empty_owned=collect_save_buffers(empty,names,false,contains,copy_guest);
        check(reads==0 && empty_owned.size()==1 && empty_owned[0].bytes.empty(),"empty main/auxiliary semantics wrong");
        // Every SIZES pointer is checked before the caller writes any output.
        const std::array<std::uint32_t,3> sizes_addresses{base+32,base+256,base+512};
        for(unsigned index=0;index<3;++index){
            auto bad=sizes_addresses;bad[index]=base+1020;
            std::array<std::uint8_t,1024> output{};output.fill(0xa5);
            if(preflight_sizes_outputs(bad,contains))output.fill(0);
            check(std::all_of(output.begin(),output.end(),[](auto x){return x==0xa5;}),"SIZES wrote output before all pointers validated");
            check(!preflight_sizes_outputs(bad,contains),"bad SIZES output accepted");
        }
        check(preflight_sizes_outputs(sizes_addresses,contains),"valid SIZES outputs rejected");
        check(preflight_sizes_outputs({0,0,0},contains),"optional SIZES outputs rejected");
        for(unsigned i=0;i<3;++i){auto p=sizes_addresses;p[i]=0xfffffff8u;check(!preflight_sizes_outputs(p,contains),"wrapping SIZES pointer accepted");}
        bool over_limit=false;auto huge=good;huge[0]={base,0xffffffffu,static_cast<std::uint32_t>(kMaxGuestSaveBytes)};huge[1]={base,1,1};
        try{preflight_save_buffers(huge,false,[](auto,auto){return true;});}catch(const std::invalid_argument&){over_limit=true;}
        check(over_limit,"aggregate size cap ignored");
        // Same-process commits must not produce a mixed two-file generation.
        bool ok1=false,ok2=false;std::string e1,e2;
        std::thread t1([&]{ok1=commit(profile,{{"DATA.BIN",a},{"ICON0.PNG",a}},e1);});
        std::thread t2([&]{ok2=commit(profile,{{"DATA.BIN",b},{"ICON0.PNG",b}},e2);});
        t1.join();t2.join();check(ok1&&ok2,"serialized commits failed");
        check(bytes(profile/"DATA.BIN")==bytes(profile/"ICON0.PNG"),"mixed generation after serialized commits");
        for(const auto&entry:fs::directory_iterator(root))check(entry.path().filename().string().rfind(".renegade-save-",0)!=0,"staging debris after normal failure/success");
        fs::remove_all(root);std::cout<<checks<<" savedata staging checks passed\n";return 0;
    }catch(const std::exception&e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<"\n";std::error_code ec;fs::remove_all(root,ec);return 1;}
}
