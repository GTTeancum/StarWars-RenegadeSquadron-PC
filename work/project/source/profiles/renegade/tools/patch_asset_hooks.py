"""Install verified ULUS10292 asset observers after AOT regeneration.

Validate all files before writing any; fail closed on duplicate/moved hooks.
Never overwrite unrelated generated instructions. --check performs no writes.
"""
import argparse
from pathlib import Path

HOOKS = {
    "0329": ("override_commands.hpp", (
        ("L_08A97B7C:", "renegade::overrides::emitted_command(rt, ctx);"),)),
    "0128": ("render_resource_trace024.hpp", (
        ("L_08905E90:", "renegade::render_trace024::submission(rt, ctx);"),)),
    "0017": ("model_trace022.hpp", (
        ("L_088267D4:", "renegade::trace_model_name023(rt, ctx);"),
        ("L_08826800:", "renegade::trace_model_load022(rt, ctx);"))),
    "0019": ("render_resource_trace024.hpp", (
        ("L_0882BA6C:", "renegade::render_trace024::name(rt, ctx);"),)),
    "0121": ("render_resource_trace024.hpp", (
        ("L_088F7428:", "renegade::render_trace024::loaded(rt, ctx);"),)),
}
GUARDS = {
    "L_08A97B7C:": "    aot_mem.aot_store32(ctx.gpr[2] + static_cast<std::uint32_t>(0), ctx.gpr[4]);\n",
    "L_08905E90:": "    ctx.gpr[5] = (ctx.gpr[5] < static_cast<std::uint32_t>(1) ? 1u : 0u);\n",
    "L_088267D4:": "    ctx.gpr[4] = (2226u << 16u);\n",
    "L_08826800:": "    ctx.gpr[31] = (aot_mem.aot_load32(ctx.gpr[29] + static_cast<std::uint32_t>(120)));\n",
    "L_0882BA6C:": "    ctx.gpr[8] = (ctx.gpr[2] + 0u);\n",
    "L_088F7428:": "    ctx.gpr[31] = (aot_mem.aot_load32(ctx.gpr[29] + static_cast<std::uint32_t>(40)));\n",
}

def prepare(directory):
    changes = []
    for unit, (header, hooks) in HOOKS.items():
        path = directory / f"generated_unit_{unit}.cpp"
        original = path.read_text(encoding="utf-8")
        text = original
        include = f'#include "../host/{header}"\n'
        if text.count(include) > 1:
            raise ValueError(f"{path.name}: duplicate observer include")
        for anchor, call in hooks:
            marker = anchor + "\n"
            line = "    " + call + "\n"
            if text.count(marker) != 1:
                raise ValueError(f"{path.name}: missing/ambiguous {anchor}")
            count = text.count(call)
            if count > 1 or (count == 1 and marker + line not in text):
                raise ValueError(f"{path.name}: misplaced/duplicate hook at {anchor}")
            expected = marker + (line if count else "") + GUARDS[anchor]
            if expected not in text:
                raise ValueError(f"{path.name}: instruction guard changed at {anchor}")
            if not count:
                text = text.replace(marker, marker + line)
        if include not in text:
            text = include + text
        if text != original:
            changes.append((path, text))
    return changes

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        changes = prepare(args.directory)
        if changes and args.check:
            raise ValueError("Asset hooks missing; reconfigure the Renegade build")
        for path, text in changes:
            newline = "\r\n" if b"\r\n" in path.read_bytes() else "\n"
            path.write_text(text, encoding="utf-8", newline=newline)
        print(f"Renegade asset hooks verified ({len(changes)} files updated)")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Asset hook validation failed: {error}\n")

if __name__ == "__main__":
    main()
