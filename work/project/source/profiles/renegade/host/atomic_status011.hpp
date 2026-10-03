#pragma once
#include <chrono>
#include <filesystem>
#include <system_error>
#include <thread>
namespace renegade::diagnostic011 {
// A polling reader may briefly deny Windows replacement. Keep the old complete
// status visible and retry the atomic rename; never delete it or truncate it.
inline void publish(const std::filesystem::path& temp,const std::filesystem::path& target,
                    std::chrono::milliseconds timeout=std::chrono::seconds(5)) {
 const auto end=std::chrono::steady_clock::now()+timeout;
 for(;;){
  std::error_code ec;std::filesystem::rename(temp,target,ec);
  if(!ec)return;
  bool transient=false;
#ifdef _WIN32
  transient=ec==std::errc::permission_denied||ec.value()==5||ec.value()==32||ec.value()==33;
#endif
  if(!transient||std::chrono::steady_clock::now()>=end)
   throw std::filesystem::filesystem_error("publish controller status",temp,target,ec);
  std::this_thread::sleep_for(std::chrono::milliseconds(10));
 }
}
}
