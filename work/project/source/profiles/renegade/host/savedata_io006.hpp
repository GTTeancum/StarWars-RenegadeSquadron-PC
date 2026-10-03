#pragma once
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>
namespace renegade::savedata {
struct Blob { std::string name; std::vector<std::uint8_t> bytes; };
void validate_component(const std::string& name, bool allow_empty = false);
void validate_paths(const std::filesystem::path& root,
                    const std::filesystem::path& directory,
                    const std::filesystem::path& data);
// Call only after validating and copying ALL guest buffers. This function accepts
// owned host bytes, never guest pointers. Does not promise power-loss durability
// or exclusion of other processes. The optional hook is for failure tests only.
bool commit(const std::filesystem::path& directory,
            const std::vector<Blob>& files, std::string& error,
            void (*before_publish)() = nullptr);
}
