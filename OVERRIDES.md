# Asset overrides (experimental)



Texture replacements support **DDS, TGA and PNG**. Model replacements use the

classic Battlefront **MSH** format. Rigid model parts and basic materials currently

work in the software renderer used by the root launcher. Whole-character skins

with explicit bone mappings are now experimental; real SWBF2 low-detail

and high-detail droids have been rendered with original game poses during a

bounded movement replay. Alignment and broader

character/LOD coverage still need validation. Advanced shaders and GPU model

rendering remain unsupported.



## Launch a pack



Put a pack anywhere on your computer. From the repository root:



```powershell

.\Play-RenegadeSquadronPC.cmd -OverridePack "work\my-pack"

```



Relative paths always resolve from the repository root. Absolute paths also work.

Use `-DryRun` to check paths and settings without starting the game. To play with

original assets, use `Play-RenegadeSquadronPC.ps1 -OverridePack ''`. Without an explicit selection, the launcher uses the local `work/mods-textures-source074` pack when it exists. The launcher clears

inherited override and discovery settings, so a previous diagnostic cannot

silently select a pack. Modern controls and XInput remain enabled as before.



Only one pack is selected per launch. Restart the game after editing its files.

No original disc files need to be changed.



## Folder layout



```

my-pack/

  textures/

    tex-v1-<64 hexadecimal characters>.png

  models/

    <original render-resource name>/

      part-0.msh

      diffuse.tga

```



For an experimental whole-character replacement, use `model.msh` and

`model.bindings` in the resource folder instead of a numbered part. Its diffuse

images must be beside the model. Bindings explicitly map classic MSH bone indices

to original pose slots and provide bind/axis/scale corrections; they are specific

to the two skeletons. See the [technical guide](outputs/MODEL-OVERRIDES-EXPERIMENTAL.md)

for the file format and [checkpoint 042](outputs/CHECKPOINT-042-WHOLE-SKIN-RENDERING.md)

for the binding design and [checkpoint 046](outputs/CHECKPOINT-046-HIGH-DETAIL-MOVEMENT.md)

for the high-detail movement test. A loaded MSH alone is insufficient for an

animated character. Invalid bindings/materials retain original geometry.



At least one of `textures` or `models` must exist. Missing replacement files keep

the corresponding original asset. Invalid/unsupported models or material images

also keep the original part, with an explanation in native output.



**Textures:** filenames identify original decoded content, not temporary memory

addresses. The ID hashes original width/height (little-endian 32-bit values) and

RGBA8 pixels. Replacement dimensions may differ and need not be powers of two.

When multiple files have the same ID, DDS takes priority, then TGA, then PNG.

Standalone texture lookup tries the next format if a candidate is invalid. Each

image must be 1–4096 pixels per dimension and at most 128 MiB on disk. DDS support

uses the bundled decoder; RGBA, BC1/DXT1, BC2/DXT3 and BC3/DXT5 are explicitly covered by current tests.

Mip chains are not retained: the decoded base image is used.



**Models:** use the exact named RSCF render resource and zero-based part slot.

Each `part-N.msh` replaces that one draw part; other parts remain original.

Whole-character replacement requires a model-specific binding file. Automatic

skeleton mapping and LOD association are not implemented. Do not infer

the resource name from a similar-looking texture or archive filename.



Place every referenced diffuse image beside its MSH. The material's referenced

stem can use DDS, TGA or PNG, in that priority order. For example, a reference to

`diffuse.tga` can use `diffuse.dds`. Directory components in references are

rejected. A missing or invalid preferred image rejects the model replacement.



## Supported material behavior



Rigid hierarchy transforms, triangle lists/strips, normals, UVs and vertex colors

are implemented. Diffuse textures use linear filtering and wrapping. Basic MSH

flags control unlit rendering, alpha blending, additive blending, double-sided

faces and alpha cutout (threshold 128). Transparent segments retain depth testing

but disable depth writes. Original game lighting and attachment transforms still

affect appearance. Scaling/orientation may need adjustment in the source MSH.



Experimental gloss-mapped materials (render type 4), and normal materials with

SPECULAR set, use diffuse texture alpha as a highlight mask and DATA specular

RGB as the tint. Highlights are added after diffuse texturing. Alpha affects

opacity only when blending, additive transparency or cutout is explicitly set.

The adapter uses the original game lights and GE shininess, not the stored MSH

exponent. For gloss overrides only, a light with zero specular RGB uses its

diffuse RGB for highlights; explicit nonzero specular RGB takes precedence. It is

vertex-lit and is not a pixel-identical SWBF2 shader. Synthetic

rendering tests pass. A high-detail droid movement replay renders successfully;

one deployment lighting case is verified in checkpoint 049. Broader lighting

and visual alignment still require review.



Cloth, shadow geometry, detail/environment maps and other special render types

remain unsupported. Glow base surfaces and per-pixel lighting are supported as described below; bloom halos remain absent. Rigid replacements reject animation and weights; experimental

whole skins need explicit bone mappings as described above.



## Discover asset IDs (advanced)



Run the launcher with discovery enabled:



```powershell

.\Play-RenegadeSquadronPC.cmd -DiscoverAssets

```



The launcher prints a unique output folder below `work/override-discovery`.

Enter the scene containing the assets you want, then close the game. The folder

contains hash-named original texture images under `textures` and named model/part

records in `models.jsonl`. Keep discovery runs short: dumping/matching textures is

currently expensive. `-DryRun -DiscoverAssets` checks settings without creating

output folders. Discovery can also be combined with `-OverridePack`.



For scripted native diagnostics, these environment variables are available

(the root launcher clears inherited values and sets its own):



- `RENEGADE_DUMP_TEXTURES`: output directory for hash-named original TGA images.

- `RENEGADE_TRACE_RENDER_RESOURCES`: JSONL filename for names, part tables and draws.

- `RENEGADE_OVERRIDE_ROOT`: pack folder for a direct native launch.

- `RENEGADE_TRACE_MODEL_DRAWS=1`: bounded replacement triangle/pixel diagnostics.

- `RENEGADE_TRACE_MODEL_TRANSFORMS`: JSONL filename for bounded original part,

  vertex-address and world/view/projection samples. Unmatched index-buffer

  candidates are marked `matched:false` and are not used for replacement.

- `RENEGADE_TRACE_MODEL_SUBMISSIONS`: experimental battle-droid-only JSONL

  trace, capped at 256 calls before empty parts are discarded. Records original

  submission matrices and caller registers for animation-adapter research.

- `RENEGADE_TRACE_COMMAND_POSES`: with a valid skin candidate, writes up to 512

  exact command-address/complete-pose associations. The trace does not enable

  replacement rendering; a valid installed skin candidate does.

- `PSPRECOMP_GE_BACKEND=software`: required for current override rendering.



Texture discovery/matching can be expensive. Use bounded diagnostic runs while

choosing IDs; optimization is unfinished. See

[the experimental technical guide](outputs/MODEL-OVERRIDES-EXPERIMENTAL.md) and

[checkpoint 027](outputs/CHECKPOINT-027-MSH-MATERIAL-FLAGS.md) for reproducible test

state. A real SWBF2 R2-D2 model/texture was visibly substituted for the Geonosis

CIS emblem as a diagnostic; this is not a production upgrade pack. Local test

assets are excluded from Git.



## Rebuilding after AOT regeneration



Renegade's CMake profile automatically reinstalls the asset hooks in regenerated

units 0017, 0019, 0121, 0128 and 0329, and watches those files for incremental builds. Python

3.10 or later is required and located by CMake. The installer validates all hook

labels and adjacent instructions before changing any file; unexpected generator

output stops configuration instead of silently building broken asset discovery.

The older `work/patch-model-trace022.py` entry point still works as a wrapper;

`--check` verifies without editing. This covers the override hooks, not every

historical game-specific source transformation.


## Local SWBF2 test pack

From the repository root, launch the locally staged battle-droid pack:

```powershell
.\Play-RenegadeSquadronPC.cmd -OverridePack "work\mods-skin053-lods"
```

It uses the SWBF2 high-detail model for `battle_droid` and the low-detail model
for both `L1#battle_droid` and `L2#battle_droid`, each with explicit skin bindings
and its texture. Local proprietary test assets are excluded from Git. This is
not an automatically optimized LOD chain. The movement run verified actual
replacement drawing for all three variants, not seamless transitions for a
tracked individual actor.

## Model names and binding authoring

See [the authoring guide](outputs/OVERRIDE-AUTHORING.md) for the extracted model catalog, original bone slots, a complete named-bone recipe and a tool that generates model.bindings.

## Global VRAM/RAM texture overrides and priority (057)

Global replacements apply to textures submitted through the software renderer,
including HUD/menu sprites, terrain, effects and unnamed resources. They do not
require an RSCF model name or model.bindings. The root launcher uses this renderer.

1. Launch with `-DiscoverAssets`, visit the screen/map containing the texture,
   then close the game. Discovery can also run with `-OverridePack`.
2. In the printed discovery folder, open `textures/`. Original decoded textures
   are saved as `tex-v1-<hash>.tga`. `textures/textures.jsonl` lists dimensions,
   guest source address, format, mip level, palette address and swizzle state.
3. Put an edited/upscaled replacement in your pack's `textures/` folder. Keep the
   exact hash stem and use `.dds`, `.tga` or `.png`. Select that pack at launch.
   The replacement keeps the ORIGINAL texture's hash name; do not hash the edited
   image to choose its filename. Different replacement dimensions are supported.

Priority for a rendered part is:

- A valid explicit MSH override uses its own material setup and referenced images.
  A global texture match cannot replace those material images or force a texture
  onto an intentionally untextured replacement segment.
- Otherwise the original geometry uses a matching global content-hash texture.
- Otherwise it uses the original texture. Invalid model overrides fall back to
  the original geometry, where a valid global texture replacement can still apply.

Within global candidates, DDS takes priority over TGA, then PNG; invalid files
try the next candidate. Mesh-material candidate validation remains atomic as
explained above. Restart after editing pack files.

The same decoded original pixels and dimensions share an ID even at different
addresses or in different source encodings. Palette/content changes can produce
new IDs, so animated/generated textures may require multiple replacement files.
Each selected mip has its own identity. Addresses in the index are provenance,
not stable replacement keys. Discovery captures encountered textures, not unknown
unused regions of raw VRAM. It dumps originals even while a pack is selected.

All 11 supported PSP source encodings are covered by renderer tests, from VRAM
and RAM, along with HUD rectangles, selected mips, palette/content changes,
swizzle changes and mesh-material priority. Source decoding and replacement
images support dimensions up to 4096. In-game checks cover menu replacements and
Geonosis discovery while the droid mesh pack is active. This does not certify
every visual asset on every map. Direct GPU override rendering remains unsupported.
A failed dump write no longer cancels an otherwise valid replacement.

## Global texture alpha policy

A global texture replacement may have a neighboring `textures/<tex-v1-hash>.json` file containing:

```json
{"alpha":"original"}
```

This uses the supplied image RGB while sampling alpha from the original guest texture at the original UVs, mip level, wrapping and filtering settings. It preserves the game's cutout/transparency behavior without modifying either image. Use only for reviewed RGB layouts; it cannot repair incompatible UV islands or foliage silhouettes.

Without a sidecar, alpha comes from the replacement image. `{"alpha":"replacement"}` explicitly requests the same default. The sidecar accepts only this single key and these two values, with a 1024-byte limit. Invalid policies retain the original texture and cache that failure until restart. Model-bound texture loads ignore this global policy and keep their existing material precedence.

## Converted map integration status (checkpoint 083)

Run `.\Capture-Converted-Map.ps1 -Map korriban`, `-Map ordmantell`, `-Map boz`, or `-Map echo` from the repo root for actual headless 1280x720 FXAA captures using the supplied converted MSH geometry, materials and authored UVs. The local extraction and dependencies must be present. Source images and orientation are preserved.

The opt-in software renderer bridge matches complete triangle strips in world space, including object transforms. Unmatched or ambiguous draws remain original. It records per-frame matched draws and triangles in `world-report.jsonl`; candidate draws also include dynamic objects and effects, so their count is not a map-completeness percentage.

RS_WORLD version 3 supports explicit, model-specific vertex bindings for known differences between converted meshes and original game geometry. These change only the geometry used for matching: rendered positions, normals, material images and UVs remain authored. Exact matching and ambiguity rejection still apply. Echo Base stages 14 bindings for the base section and 11 for an additional translated matching instance, with source hashes and full draw topology verified before capture. Versions 1/2 retain their original behavior. See checkpoints 087/088 for the visual results and limits.

Static visible model surfaces can load alongside supplied shadow-volume data. Type-6 volume nodes are excluded from surface rasterization, and the runtime warns that supplied volume payloads are not rendered. This does not implement a new shadow pass. Animated/cloth models and models with no visible surfaces still reject atomically.

Material types 27/28 load normal/bump images and evaluate lighting per pixel. `.tga.option` bump settings are honored; tangent-space normals use the authored UV basis. Normalmapped gloss uses normal/bump alpha; standard gloss uses diffuse alpha. If an authored normal/gloss image is missing, those highlights are disabled. Per-pixel materials use the stored MSH specular exponent. Glow surfaces use an emissive base pass; bloom halos remain absent.

Korriban's supplied archive contains normal-map option files but omits 25 referenced secondary images used by the staged base models. Those surfaces use their supplied diffuse textures with geometric normals; warnings and audit fields explicitly retain the missing effects. Invalid present normal images reject the model, and missing diffuse images always reject it. Scrolling, environment/refraction materials, invalid normals and unmatched geometry still require work. This does not establish all-map completion or normal interactive HD presentation.

### Converted Ord Mantell capture (checkpoint 082)

The original `.\Capture-Converted-OrdMantell.ps1` remains available for its recorded Ord Mantell replay. Use the generic launcher above for the current verified map choices and per-frame coverage reports. See `outputs/CHECKPOINT-082.md` for the first integration evidence and `outputs/CHECKPOINT-083.md` for current behavior.

