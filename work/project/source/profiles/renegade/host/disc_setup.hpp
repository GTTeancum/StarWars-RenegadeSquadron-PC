#pragma once
// Minimal read-only ISO9660 extraction for user-owned PSP discs. No mount,
// shell invocation, external extractor, or write to the original ISO.
#include <algorithm>
#include <array>
#include <cctype>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#endif
#include "psprecomp/sha256.hpp"
namespace renegade::disc_setup {
namespace fs = std::filesystem;
struct Entry {
  fs::path path;
  std::uint32_t sector{}, size{};
  bool directory{};
};
inline std::uint32_t le32(const unsigned char *p) {
  return p[0] | (std::uint32_t(p[1]) << 8) | (std::uint32_t(p[2]) << 16) |
         (std::uint32_t(p[3]) << 24);
}
class Iso {
  std::ifstream input;
  std::uint64_t size;
  std::set<std::uint32_t> visited;
  std::vector<unsigned char> read(std::uint64_t offset, std::size_t bytes) {
    if (offset > size || bytes > size - offset)
      throw std::runtime_error("ISO extent is outside the file");
    std::vector<unsigned char> out(bytes);
    input.seekg(std::streamoff(offset));
    input.read(reinterpret_cast<char *>(out.data()), std::streamsize(bytes));
    if (!input)
      throw std::runtime_error("Cannot read game ISO");
    return out;
  }
  void directory(std::uint32_t sector, std::uint32_t bytes,
                 const fs::path &parent, std::vector<Entry> &entries,
                 unsigned depth) {
    if (depth > 16 || bytes > 16 * 1024 * 1024 ||
        !visited.insert(sector).second)
      throw std::runtime_error("Invalid or cyclic ISO directory");
    auto data = read(std::uint64_t(sector) * 2048, bytes);
    for (std::size_t at = 0; at < data.size();) {
      unsigned length = data[at];
      if (!length) {
        at = ((at / 2048) + 1) * 2048;
        continue;
      }
      if (length < 34 || at + length > data.size() ||
          (at % 2048) + length > 2048)
        throw std::runtime_error("Invalid ISO directory record");
      const auto *r = data.data() + at;
      unsigned n = r[32];
      if (33 + n > length)
        throw std::runtime_error("Invalid ISO filename length");
      at += length;
      if (n == 1 && (r[33] == 0 || r[33] == 1))
        continue;
      std::string name(reinterpret_cast<const char *>(r + 33), n);
      if (auto sem = name.find(';'); sem != std::string::npos)
        name.resize(sem);
      if (!name.empty() && name.back() == '.')
        name.pop_back();
      if (name.empty() || name == "." || name == ".." ||
          name.find_first_of("\\/:*?\"<>|") != std::string::npos ||
          name.back() == ' ' || name.back() == '.' ||
          std::any_of(name.begin(), name.end(),
                      [](unsigned char c) { return c < 32 || c >= 127; }))
        throw std::runtime_error("Unsafe filename in game ISO");
      std::string upper = name;
      for (auto &c : upper)
        c = char(std::toupper(static_cast<unsigned char>(c)));
      auto stem = upper.substr(0, upper.find('.'));
      if (stem == "CON" || stem == "PRN" || stem == "AUX" || stem == "NUL" ||
          (stem.size() == 4 &&
           (stem.starts_with("COM") || stem.starts_with("LPT")) &&
           stem[3] >= '0' && stem[3] <= '9'))
        throw std::runtime_error("Reserved filename in ISO");
      if (parent.empty() && upper != "PSP_GAME")
        continue;
      if (r[1] || r[26] || r[27] || (r[25] & 128))
        throw std::runtime_error(
            "Unsupported ISO interleaving or multi-extent file");
      Entry e{parent / upper, le32(r + 2), le32(r + 10), bool(r[25] & 2)};
      if (std::uint64_t(e.sector) * 2048 + e.size > size)
        throw std::runtime_error("ISO file exceeds image size");
      entries.push_back(e);
      if (entries.size() > 100000)
        throw std::runtime_error("Too many files in ISO");
      if (e.directory)
        directory(e.sector, e.size, e.path, entries, depth + 1);
    }
  }

public:
  explicit Iso(const fs::path &path)
      : input(path, std::ios::binary), size(fs::file_size(path)) {
    if (!input)
      throw std::runtime_error("Cannot open game ISO");
  }
  std::vector<Entry> entries() {
    for (unsigned sector = 16; sector < 80; ++sector) {
      auto p = read(sector * 2048ull, 2048);
      if (std::string(reinterpret_cast<const char *>(p.data() + 1), 5) !=
              "CD001" ||
          p[6] != 1)
        throw std::runtime_error("Not an ISO9660 PSP disc image");
      if (p[0] == 255)
        break;
      if (p[0] == 1) {
        if (p[128] != 0 || p[129] != 8)
          throw std::runtime_error("ISO sector size must be 2048");
        std::vector<Entry> out;
        directory(le32(p.data() + 158), le32(p.data() + 166), {}, out, 0);
        if (out.empty())
          throw std::runtime_error("ISO has no PSP_GAME directory");
        return out;
      }
    }
    throw std::runtime_error("ISO has no primary volume descriptor");
  }
  void extract(const Entry &e, const fs::path &path) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out)
      throw std::runtime_error("Cannot create extracted game file");
    std::vector<char> buffer(1024 * 1024);
    input.seekg(std::uint64_t(e.sector) * 2048);
    for (std::uint64_t remaining = e.size; remaining;) {
      auto count = std::min<std::uint64_t>(remaining, buffer.size());
      input.read(buffer.data(), std::streamsize(count));
      out.write(buffer.data(), std::streamsize(count));
      if (!input || !out)
        throw std::runtime_error(
            "Game extraction failed; check free disk space");
      remaining -= count;
    }
  }
};
inline void reject_links(const fs::path &path) {
  for (fs::path p = fs::absolute(path); !p.empty(); p = p.parent_path()) {
    if (fs::is_symlink(fs::symlink_status(p)))
      throw std::runtime_error(
          "Extraction destination must not contain symbolic links");
#ifdef _WIN32
    auto attrs = GetFileAttributesW(p.c_str());
    if (attrs != INVALID_FILE_ATTRIBUTES &&
        (attrs & FILE_ATTRIBUTE_REPARSE_POINT))
      throw std::runtime_error("Extraction destination must not contain "
                               "junctions or reparse points");
#endif
    if (p == p.parent_path())
      break;
  }
}
inline bool complete(const fs::path &disc) {
  return fs::is_regular_file(disc / "PSP_GAME/SYSDIR/BOOT.BIN") &&
         fs::is_regular_file(disc / "PSP_GAME/PARAM.SFO") &&
         fs::is_directory(disc / "PSP_GAME/USRDIR");
}
inline void prepare(const fs::path &root) {
  const auto disc = root / "data";
  if (complete(disc))
    return;
  reject_links(disc);
  if (fs::exists(disc / "PSP_GAME"))
    throw std::runtime_error(
        "data/PSP_GAME is incomplete. Move that incomplete folder aside and "
        "run again to extract your ISO.");
  std::vector<fs::path> images;
  for (const auto &e : fs::directory_iterator(root)) {
    auto ext = e.path().extension().string();
    for (auto &c : ext)
      c = char(std::tolower(static_cast<unsigned char>(c)));
    if (e.is_regular_file() && ext == ".iso")
      images.push_back(e.path());
  }
  if (images.empty())
    throw std::runtime_error(
        "Place your US Renegade Squadron ISO beside RenegadeSquadron.exe. "
        "First launch extracts it automatically into data/PSP_GAME.");
  if (images.size() != 1)
    throw std::runtime_error(
        "More than one ISO found. Leave only the US Renegade Squadron ISO "
        "beside RenegadeSquadron.exe for first-run setup.");
  Iso iso(images[0]);
  const auto entries = iso.entries();
  std::set<fs::path> unique;
  for (const auto &e : entries)
    if (!unique.insert(e.path).second)
      throw std::runtime_error("Duplicate ISO filename");
  const auto stage =
      disc / (".iso-extracting-" +
              std::to_string(
                  std::chrono::steady_clock::now().time_since_epoch().count()));
  reject_links(stage);
  fs::create_directories(stage);
  std::cerr << "[setup] Extracting " << images[0].filename().string()
            << " into data/PSP_GAME; the ISO is unchanged.\n";
  for (const auto &e : entries) {
    const auto path = stage / e.path;
    reject_links(path);
    if (e.directory)
      fs::create_directories(path);
    else {
      fs::create_directories(path.parent_path());
      iso.extract(e, path);
    }
  }
  if (!complete(stage) ||
      psprecomp::sha256_file(stage / "PSP_GAME/SYSDIR/BOOT.BIN") !=
          "f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68" ||
      psprecomp::sha256_file(stage / "PSP_GAME/PARAM.SFO") !=
          "18c944abd8f28b44c95719d27211d0ec6dcb00a535c0ca1c60ff03658d584fd4")
    throw std::runtime_error(
        "Extracted ISO does not match the supported US disc (ULUS10292)");
  fs::rename(stage / "PSP_GAME", disc / "PSP_GAME");
  fs::remove(stage);
  std::cerr << "[setup] US disc verified; extraction complete.\n";
}
} // namespace renegade::disc_setup
