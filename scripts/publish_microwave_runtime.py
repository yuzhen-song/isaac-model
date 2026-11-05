#!/usr/bin/env python3
"""Archive an existing server run and publish it; does not run Isaac Sim."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = "yuzhen-song/isaac-model"
DEFAULT_SOURCE = "/root/autodl-tmp/microwave_updated/Microwave_Isaac_Handoff"
ASSETS = (
    "microwave_test.usda", "microwave_fixed_base.usda", "joint_parameters.json",
    "mass_estimate.json", "requirements.txt", "run_passive_scene.py",
    "run_isaac_check.py", "record_microwave_motion.py",
)
REPORTS = {
    "runtime_results/passive_scene_result.json": "validation/passive_scene_result.json",
    "runtime_results/runtime_result.json": "validation/runtime_result.json",
    "runtime_results/joint_motion.csv": "validation/joint_motion.csv",
    "microwave_open_close.json": "validation/microwave_open_close.json",
    "microwave_open_close.csv": "validation/microwave_open_close.csv",
    "microwave_open_close.mp4": "media/microwave_open_close.mp4",
}


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(source):
    mapping = {name: name for name in ASSETS}
    mapping.update(REPORTS)
    for name in ("source_cad", "meshes_assembly_mm", "meshes_sim_m", "docs"):
        folder = source / name
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("Missing or symlinked asset directory: " + str(folder))
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlink in asset directory: " + str(path))
            if path.is_file():
                relative = path.relative_to(source).as_posix()
                mapping[relative] = relative
    for name in ("passive_check.log", "joint_check.log", "record_video.log"):
        if (source / name).is_file():
            mapping[name] = "validation/logs/" + name
    for relative in mapping:
        path = source / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing actual-run file: " + str(path))
        if not path.resolve().is_relative_to(source):
            raise ValueError("File is outside the source directory: " + str(path))
        if path.stat().st_size >= 95 * 1024 * 1024:
            raise ValueError("File needs separate large-file handling: " + str(path))
    return mapping


def read_reports(source):
    paths = ("runtime_results/passive_scene_result.json",
             "runtime_results/runtime_result.json", "microwave_open_close.json")
    reports = [json.loads((source / name).read_text(encoding="utf-8-sig")) for name in paths]
    if not all(isinstance(item, dict) for item in reports):
        raise ValueError("Runtime reports must contain JSON objects")
    return reports


def archive(source, repo_root, revision):
    """Copy only delivered assets and known run outputs; retain current README."""
    mapping = source_files(source)
    passive, joint, recording = read_reports(source)
    destination = repo_root / "objects/microwave"
    summary_path = destination / "validation/runtime_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    old_video = destination / "media/microwave_open_close.mp4"
    same_video = old_video.is_file() and digest(old_video) == digest(source / "microwave_open_close.mp4")
    for relative, target in mapping.items():
        output = destination / target
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, output)
        if digest(output) != digest(source / relative):
            raise ValueError("Source changed while copying: " + str(source / relative))
    flags = {
        "passive_supported_poses": passive.get("finite_supported_poses_observed") is True,
        "joint_report_passed": joint.get("passed") is True,
        "recording_report_passed": recording.get("motion_checks_passed") is True,
    }
    for name, report in (("joint", joint), ("recording", recording)):
        checks = report.get("checks")
        flags[name + "_individual_checks"] = bool(checks) and isinstance(checks, dict) and all(
            value is True for value in checks.values())
    now = datetime.now(timezone.utc).isoformat()
    summary.update({
        "source": "Actual server run files archived by scripts/publish_microwave_runtime.py",
        "numeric_runtime_reports_archived": True,
        "numeric_tracking_pass_independently_verified": False,
        "verification_scope": "Reads archived report flags; does not rerun or independently reproduce the simulation",
        "reported_check_flags": flags,
        "all_reported_checks_passed": all(flags.values()),
        "archived_at_utc": now,
        "report_paths": list(REPORTS.values()),
        "video_metadata_verified": bool(summary.get("video_metadata_verified")) and same_video,
    })
    if not same_video:
        summary["video"] = {
            "path": "media/microwave_open_close.mp4", "size_bytes": old_video.stat().st_size,
            "frames": recording.get("frames"), "fps": recording.get("fps"),
            "duration_s": recording.get("duration_s"), "metadata_source": "recording report",
        }
    dump(summary_path, summary)
    dump(destination / "validation/runtime_source_manifest.json", {
        "source_directory": str(source), "archived_at_utc": now, "base_repository_commit": revision,
        "files": [{"source": name, "archived": target, "bytes": (source / name).stat().st_size,
                   "sha256": digest(source / name)} for name, target in sorted(mapping.items())],
    })
    readme = destination / "README.md"
    text = readme.read_text(encoding="utf-8")
    if not same_video:
        text = text.replace(
            "[开关门视频](media/microwave_open_close.mp4)已归档并核对视频元数据：330 帧、30 fps、11 秒、1280×720。",
            "[开关门视频](media/microwave_open_close.mp4)已从服务器归档；元数据来源见运行摘要。")
    text = text.replace(
        "微波炉数值运行报告尚未归档，因此没有独立复核其跟踪判据；验证来源见 [运行摘要](validation/runtime_summary.json)。",
        "服务器数值运行报告已归档；逐项结果和验证范围见 [运行摘要](validation/runtime_summary.json)。")
    marker = "\n## 服务器运行归档\n"
    text = text.split(marker)[0].rstrip() + marker + "\n"
    text += "实际运行的 USD、脚本、参数及网格已同步。JSON/CSV 位于 `validation/`，视频位于 `media/`。\n"
    text += "存在的测试日志位于 `validation/logs/`；源文件 SHA-256 见 `validation/runtime_source_manifest.json`。\n"
    text += "报告标志汇总：**" + ("全部通过" if all(flags.values()) else "存在失败或缺失标志") + "**。\n"
    text += "此归档读取服务器报告，不代表在另一环境独立复现。\n"
    readme.write_text(text, encoding="utf-8")
    root_readme = repo_root / "README.md"
    text = root_readme.read_text(encoding="utf-8")
    text = text.replace(
        "  reports successful checks/recording, and its archived video has 330 frames at\n"
        "  30 fps, 1280×720, lasting 11 seconds. Microwave numeric runtime reports have not\n"
        "  yet been archived; its summary identifies this distinction.",
        "  reports successful checks/recording. Microwave server JSON/CSV reports and\n"
        "  available logs are archived under `objects/microwave/validation/`; read its\n"
        "  runtime summary for actual pass/fail flags and the scope of the checks.")
    root_readme.write_text(text, encoding="utf-8")
    dump(destination / "manifest.json", {
        "files": [{"file": p.relative_to(destination).as_posix(), "bytes": p.stat().st_size,
                   "sha256": digest(p)} for p in sorted(destination.rglob("*"))
                  if p.is_file() and p.name != "manifest.json"],
        "runtime_status": "see validation/runtime_summary.json",
    })
    return flags


def run(command, cwd=None, capture=False):
    result = subprocess.run(command, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--dry-run", action="store_true", help="Check source files without connecting or writing")
    args = parser.parse_args()
    source = Path(args.source).resolve(strict=True)
    mapping = source_files(source)
    read_reports(source)
    if args.dry_run:
        print(json.dumps(mapping, indent=2))
        return
    for executable in ("git", "gh"):
        if shutil.which(executable) is None:
            raise RuntimeError("Required command not installed: " + executable)
    run(["gh", "auth", "status", "--hostname", "github.com"])
    user = json.loads(run(["gh", "api", "user"], capture=True))
    work = Path(tempfile.mkdtemp(prefix="isaac-model-runtime-"))
    print("Working copy retained at: " + str(work), flush=True)
    git = ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]
    run(git + ["clone", "--depth", "1", "--branch", "main", "https://github.com/" + REPO + ".git", str(work)])
    revision = run(git + ["rev-parse", "HEAD"], cwd=work, capture=True)
    flags = archive(source, work, revision)
    print(json.dumps({"reported_check_flags": flags}, indent=2), flush=True)
    run(git + ["config", "user.name", user.get("name") or user["login"]], cwd=work)
    run(git + ["config", "user.email", str(user["id"]) + "+" + user["login"] + "@users.noreply.github.com"], cwd=work)
    run(git + ["add", "README.md", "objects/microwave"], cwd=work)
    logs = work / "objects/microwave/validation/logs"
    if logs.is_dir():
        run(git + ["add", "-f", "objects/microwave/validation/logs"], cwd=work)
    run(git + ["diff", "--cached", "--stat"], cwd=work)
    run(git + ["commit", "-m", "Archive actual microwave server assets and runtime evidence"], cwd=work)
    run(git + ["push", "origin", "HEAD:main"], cwd=work)
    print("Uploaded: https://github.com/" + REPO + "/tree/main/objects/microwave")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print("Upload stopped: " + str(error), file=sys.stderr)
        sys.exit(1)
