"""Replay one Instant Action menu record on the rebuilt native binary."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
PYTHON = Path(r"C:\Users\LRPC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")


def read_json(path):
    return json.loads(path.read_text())


def wait_paused(run, vblank, timeout=1800):
    control = ROOT / "runs" / ("control-" + run)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state_path = ROOT / "runs" / run / "run.json"
        if state_path.exists():
            run_state = read_json(state_path)
            if run_state.get("exit_code") is not None:
                raise RuntimeError(f"{run} terminal before vblank {vblank}: {run_state.get('exit_code')}")
        try:
            status = read_json(control / "status.json")
            if status["paused"] and status["vblank"] == vblank:
                return status
        except (OSError, json.JSONDecodeError):
            pass
        time.sleep(0.2)
    raise TimeoutError(f"{run} did not pause at vblank {vblank}")


def save_frame(run, status):
    control = ROOT / "runs" / ("control-" + run)
    out = ROOT.parent / "outputs" / f"{run}-vblank{status['vblank']}.png"
    Image.open(control / status["frame"]).save(out)
    return out


def step(run, frames, **kwargs):
    args = [str(PYTHON), str(ROOT / "step011.py"), run, str(frames)]
    for key, value in kwargs.items():
        args.extend(["--" + key.replace("_", "-"), str(value)])
    subprocess.run(args, check=True)
    status = read_json(ROOT / "runs" / ("control-" + run) / "status.json")
    return status, ROOT.parent / "outputs" / f"{run}-vblank{status['vblank']}.png"


def publish(path, text):
    temp = path.with_suffix(path.suffix + ".next")
    temp.write_text(text)
    deadline = time.monotonic() + 5
    while True:
        try:
            temp.replace(path)
            return
        except PermissionError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.01)


def stop_run(run):
    control = ROOT / "runs" / ("control-" + run)
    status = read_json(control / "status.json")
    publish(control / "command.txt", f"{int(status['sequence']) + 1} 0 0 128 128\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("record", type=Path)
    parser.add_argument("--through", type=int, required=True)
    parser.add_argument("--ground-spawn", action="store_true")
    parser.add_argument("--space-spawn", action="store_true")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()

    launch = subprocess.Popen([
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(ROOT / "launch-instant015.ps1"), args.run,
    ], cwd=str(ROOT.parent), text=True)
    summary = {
        "run": args.run,
        "record": str(args.record),
        "through": args.through,
        "ground_spawn": args.ground_spawn,
        "space_spawn": args.space_spawn,
        "started": time.time(),
    }
    try:
        wait_paused(args.run, 1400)
        (ROOT / "runs" / ("gamepad-" + args.run + ".txt")).write_text("0 1 0 0 0 0 0 0 0\n")
        subprocess.run([
            str(PYTHON), str(ROOT / "replay-adaptive011.py"), args.run,
            str(args.record), "--through", str(args.through),
        ], check=True)
        status = read_json(ROOT / "runs" / ("control-" + args.run) / "status.json")
        images = [str(save_frame(args.run, status))]
        if args.ground_spawn:
            status, image = step(args.run, 12, psp=16384)
            images.append(str(image))
            status, image = step(args.run, 120, psp=0)
            images.append(str(image))
            status, image = step(args.run, 12, psp=16384)
            images.append(str(image))
            status, image = step(args.run, 240, psp=0)
            images.append(str(image))
        elif args.space_spawn:
            status, image = step(args.run, 12, psp=16384)
            images.append(str(image))
            status, image = step(args.run, 360, psp=0)
            images.append(str(image))
        summary["final_status"] = status
        summary["images"] = images
        run_state = read_json(ROOT / "runs" / args.run / "run.json")
        summary["run_state_before_stop"] = run_state
    finally:
        if args.stop:
            try:
                stop_run(args.run)
            except Exception as exc:
                summary["stop_error"] = repr(exc)
        try:
            launch.wait(timeout=20)
        except subprocess.TimeoutExpired:
            summary["launch_wait_timeout"] = True
        state_path = ROOT / "runs" / args.run / "run.json"
        if state_path.exists():
            summary["run_state_after_stop"] = read_json(state_path)
        (ROOT.parent / "outputs" / f"{args.run}-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
