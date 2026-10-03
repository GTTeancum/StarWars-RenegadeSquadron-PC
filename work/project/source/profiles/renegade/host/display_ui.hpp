#pragma once
// Native host output sizing only. This never changes PSP memory or projection.
#include <array>
#include <cstdint>
#include <string_view>
namespace renegade::ui {
constexpr int toolbar_height = 40;
struct Resolution { int width; int height; const char* label; };
inline constexpr std::array<Resolution,6> resolutions{{
 {480,272,"480 X 272 (1X)"}, {960,544,"960 X 544 (2X)"},
 {1440,816,"1440 X 816 (3X)"}, {1920,1088,"1920 X 1088 (4X)"},
 {1280,720,"1280 X 720 (720P)"}, {1920,1080,"1920 X 1080 (1080P)"}
}};
struct Rect { int x{},y{},w{},h{}; };
inline constexpr Rect selector{162,6,282,28};
inline constexpr int row_height = 30;
inline bool inside(Rect r, int x, int y) noexcept {
 return r.w>0 && r.h>0 && x>=r.x && y>=r.y &&
        std::int64_t(x)<std::int64_t(r.x)+r.w && std::int64_t(y)<std::int64_t(r.y)+r.h;
}
inline int selected_row(int x,int y) noexcept {
 const Rect popup{selector.x,toolbar_height,selector.w,int(resolutions.size())*row_height};
 return inside(popup,x,y) ? (y-popup.y)/row_height : -1;
}
// Exact supported values only. A malformed setting is an actionable error,
// never a giant allocation or an arbitrary atoi() result.
inline int parse_resolution(std::string_view value) noexcept {
 for (int i=0;i<int(resolutions.size());++i) {
  const auto& r=resolutions[i];
  // Avoid locale/regex libraries in this small host-side parser.
  char buffer[32]{}; auto p=buffer;
  auto put=[&](int n) { char digits[10]; int k=0; do{digits[k++]=char('0'+n%10);n/=10;}while(n);while(k)*p++=digits[--k]; };
  put(r.width); *p++='x'; put(r.height);
  if(value==std::string_view(buffer,p-buffer)) return i;
 }
 return -1;
}
inline Rect fit(int output_width,int output_height,int source_width,int source_height,
                int toolbar_pixels=toolbar_height) noexcept {
 if(output_width<=0 || output_height<=toolbar_pixels || toolbar_pixels<0 ||
    source_width<=0 || source_height<=0) return {};
 Rect r{0,toolbar_pixels,output_width,output_height-toolbar_pixels};
 if(std::int64_t(r.w)*source_height > std::int64_t(r.h)*source_width) {
  const int w=int(std::int64_t(r.h)*source_width/source_height);
  r.x=(r.w-w)/2; r.w=w;
 } else {
  const int h=int(std::int64_t(r.w)*source_height/source_width);
  r.y+=(r.h-h)/2; r.h=h;
 }
 return r;
}
} // namespace renegade::ui
