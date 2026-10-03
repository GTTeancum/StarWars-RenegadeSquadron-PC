#include "savedata_io006.hpp"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <fstream>
#include <mutex>
#include <set>
#include <stdexcept>
#include <system_error>

namespace renegade::savedata {
namespace {
namespace fs = std::filesystem;
constexpr std::uintmax_t kMaxBytes = 64ull * 1024 * 1024;
constexpr std::size_t kMaxFiles = 256;
std::mutex transaction_mutex;
std::atomic<unsigned long long> serial{0};
std::string folded(std::string s) {
    for (char& c : s) if (c >= 'a' && c <= 'z') c = char(c - 'a' + 'A');
    return s;
}
fs::file_status status_of(const fs::path& path) {
    std::error_code ec;
    auto s = fs::symlink_status(path, ec);
    if (ec && ec != std::errc::no_such_file_or_directory)
        throw fs::filesystem_error("Cannot inspect savedata path", path, ec);
    return s;
}
void require_directory_or_absent(const fs::path& path) {
    const auto s = status_of(path);
    if (fs::is_symlink(s) || (fs::exists(s) && !fs::is_directory(s)))
        throw std::invalid_argument("Savedata directory is a link or is not a directory");
}
void checked_total(std::uintmax_t& total, std::uintmax_t add) {
    if (add > kMaxBytes || total > kMaxBytes - add)
        throw std::invalid_argument("Savedata transaction exceeds 64 MiB");
    total += add;
}
}
void validate_component(const std::string& name, bool allow_empty) {
    if (name.empty()) {
        if (allow_empty) return;
        throw std::invalid_argument("Empty savedata path component");
    }
    if (name == "." || name == ".." || name.back() == '.' || name.back() == ' ')
        throw std::invalid_argument("Ambiguous savedata path component");
    for (unsigned char c : name) {
        if (c < 32 || c >= 127 || c == '/' || c == '\\' || c == ':' ||
            c == '<' || c == '>' || c == '|' || c == '?' || c == '*' || c == '"')
            throw std::invalid_argument("Unsafe savedata path component");
    }
    const auto base = folded(name.substr(0, name.find('.')));
    if (base == "CON" || base == "PRN" || base == "AUX" || base == "NUL" ||
        (base.size() == 4 && (base.substr(0,3) == "COM" || base.substr(0,3) == "LPT") &&
         base[3] >= '1' && base[3] <= '9'))
        throw std::invalid_argument("Reserved savedata path component");
}
void validate_paths(const std::filesystem::path& root,
                    const std::filesystem::path& directory,
                    const std::filesystem::path& data) {
    namespace fs = std::filesystem;
    const auto r = fs::absolute(root).lexically_normal();
    const auto d = fs::absolute(directory).lexically_normal();
    const auto p = fs::absolute(data).lexically_normal();
    if (d.parent_path() != r || p.parent_path() != d)
        throw std::invalid_argument("Savedata path escapes its designated directory");
    validate_component(d.filename().string());
    validate_component(p.filename().string());
    require_directory_or_absent(r);
    require_directory_or_absent(d);
    const auto s = status_of(p);
    if (fs::is_symlink(s) || (fs::exists(s) && !fs::is_regular_file(s)))
        throw std::invalid_argument("Savedata file is a link or is not a regular file");
}
bool commit(const std::filesystem::path& directory,
            const std::vector<Blob>& files, std::string& error,
            void (*before_publish)()) {
    namespace fs = std::filesystem;
    std::lock_guard<std::mutex> lock(transaction_mutex);
    error.clear();
    fs::path transaction, previous, target;
    bool moved_old = false;
    try {
        if (files.empty() || files.size() > 5)
            throw std::invalid_argument("Savedata transaction needs one to five blobs");
        target = fs::absolute(directory).lexically_normal();
        validate_component(target.filename().string());
        const auto root = target.parent_path();
        require_directory_or_absent(root);
        require_directory_or_absent(target);
        std::set<std::string> replacements;
        std::uintmax_t input_total = 0;
        for (const auto& b : files) {
            validate_component(b.name);
            if (!replacements.insert(folded(b.name)).second)
                throw std::invalid_argument("Duplicate case-insensitive savedata name");
            checked_total(input_total, b.bytes.size());
            validate_paths(root, target, target / b.name);
        }
        // Validation above finishes before creating or replacing profile data.
        fs::create_directories(root);
        for (unsigned attempt = 0; attempt != 100; ++attempt) {
            auto tick = std::chrono::steady_clock::now().time_since_epoch().count();
            auto candidate = root / (".renegade-save-" + std::to_string(tick) + "-" + std::to_string(serial++));
            if (fs::create_directory(candidate)) { transaction = std::move(candidate); break; }
        }
        if (transaction.empty()) throw std::runtime_error("Cannot reserve savedata staging directory");
        const auto staged = transaction / "new";
        previous = transaction / "previous";
        fs::create_directory(staged);
        std::set<std::string> existing_names;
        std::uintmax_t staged_bytes = input_total;
        std::size_t retained_count = 0;
        if (fs::exists(status_of(target))) {
            for (const auto& entry : fs::directory_iterator(target)) {
                const auto name = entry.path().filename().string();
                validate_component(name);
                const auto s = entry.symlink_status();
                if (!fs::is_regular_file(s) || fs::is_symlink(s))
                    throw std::invalid_argument("Profile contains a link or nested directory");
                if (!existing_names.insert(folded(name)).second)
                    throw std::invalid_argument("Profile contains case-colliding names");
                if (existing_names.size() > kMaxFiles)
                    throw std::invalid_argument("Profile contains too many files");
                if (replacements.count(folded(name))) continue;
                checked_total(staged_bytes, entry.file_size());
                if (++retained_count + files.size() > kMaxFiles)
                    throw std::invalid_argument("Published profile would contain too many files");
                fs::copy_file(entry.path(), staged / name, fs::copy_options::none);
            }
        }
        for (const auto& b : files) {
            std::ofstream f;
            f.exceptions(std::ios::failbit | std::ios::badbit);
            f.open(staged / b.name, std::ios::binary | std::ios::out | std::ios::trunc);
            if (!b.bytes.empty()) f.write(reinterpret_cast<const char*>(b.bytes.data()), static_cast<std::streamsize>(b.bytes.size()));
            f.flush();
            f.close();
        }
        require_directory_or_absent(target);
        if (fs::exists(status_of(target))) { fs::rename(target, previous); moved_old = true; }
        if (before_publish) before_publish();
        fs::rename(staged, target);
        std::error_code cleanup_error;
        fs::remove_all(transaction, cleanup_error);
        if (cleanup_error) error = "Save committed; staging cleanup failed: " + cleanup_error.message();
        return true;
    } catch (const std::exception& e) {
        error = e.what();
        bool keep_backup = false;
        if (moved_old) {
            std::error_code rollback_error;
            fs::rename(previous, target, rollback_error);
            if (rollback_error) {
                keep_backup = true;
                error += "; rollback failed; previous profile retained at " + previous.string() + ": " + rollback_error.message();
            }
        }
        if (!transaction.empty() && !keep_backup) {
            std::error_code ignored;
            fs::remove_all(transaction, ignored);
        }
        return false;
    }
}
}
