"""Google Drive review area, via rclone.

The cloud job never posts straight to the Page. It renders the day's creatives
into a Drive folder called `Pending`; you look at them on your phone and drag
the good ones into `Approved`; a later run posts whatever is in `Approved` and
moves it to `Posted`. `Posted` is what stops anything going out twice - the
file is simply no longer in a folder the publisher looks at.

Every call is pinned to one review folder by its Drive ID
(``--drive-root-folder-id``). Without that pin a `drive.file`-scoped remote
happily creates a second folder with the same name and the approvals quietly
land somewhere the publisher never reads.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

PENDING = "Pending"
APPROVED = "Approved"
POSTED = "Posted"
FOLDERS = (PENDING, APPROVED, POSTED)

SIDECAR_SUFFIX = ".json"


class DriveError(RuntimeError):
    pass


def _config_value(key: str, env: str) -> str:
    """Drive settings come from the environment in the cloud, config.json locally."""
    value = os.environ.get(env)
    if value:
        return value.strip()

    from . import brand  # local import keeps this module importable standalone

    config_file = brand.ROOT / "config.json"
    if config_file.is_file():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if data.get(key):
            return str(data[key]).strip()
    return ""


def rclone_exe() -> str:
    exe = os.environ.get("RCLONE_EXE") or shutil.which("rclone")
    if not exe:
        raise DriveError(
            "rclone not found. Install it (winget install Rclone.Rclone) or set "
            "RCLONE_EXE to its full path."
        )
    return exe


class Review:
    """The Pending / Approved / Posted folders inside one Drive review folder."""

    def __init__(self, remote: str | None = None, folder_id: str | None = None):
        self.remote = remote or _config_value("drive_remote", "DRIVE_REMOTE")
        self.folder_id = folder_id or _config_value(
            "drive_review_folder_id", "DRIVE_REVIEW_FOLDER_ID")
        if not self.remote:
            raise DriveError(
                "No Drive remote configured. Set DRIVE_REMOTE (or drive_remote "
                "in config.json) to the rclone remote name - see SETUP-CLOUD.md."
            )
        if not self.folder_id:
            raise DriveError(
                "No Drive review folder configured. Set DRIVE_REVIEW_FOLDER_ID "
                "(or drive_review_folder_id in config.json) to the folder's ID "
                "from its Drive URL - see SETUP-CLOUD.md."
            )
        self.exe = rclone_exe()

    # -- plumbing ---------------------------------------------------------

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        command = [self.exe, "--drive-root-folder-id", self.folder_id, *args]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=600)
        if check and proc.returncode != 0:
            raise DriveError(
                f"rclone {' '.join(args[:2])} failed ({proc.returncode}): "
                f"{(proc.stderr or proc.stdout).strip()[:400]}"
            )
        return proc

    def _path(self, folder: str, name: str = "") -> str:
        return f"{self.remote}:{folder}/{name}" if name else f"{self.remote}:{folder}"

    # -- operations -------------------------------------------------------

    def ensure_folders(self) -> None:
        for folder in FOLDERS:
            self._run("mkdir", self._path(folder), check=False)

    def list_files(self, folder: str, suffix: str = ".jpg") -> list[str]:
        proc = self._run("lsf", self._path(folder), "--include", f"*{suffix}",
                         check=False)
        if proc.returncode != 0:
            return []
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    def upload(self, local: Path, folder: str, name: str | None = None) -> None:
        local = Path(local)
        if not local.is_file():
            raise DriveError(f"Nothing to upload - {local} does not exist.")
        self._run("copyto", str(local), self._path(folder, name or local.name))

    def download(self, folder: str, name: str, local: Path) -> bool:
        local = Path(local)
        local.parent.mkdir(parents=True, exist_ok=True)
        proc = self._run("copyto", self._path(folder, name), str(local), check=False)
        return proc.returncode == 0 and local.is_file()

    def move(self, src_folder: str, dst_folder: str, name: str) -> None:
        self._run("moveto", self._path(src_folder, name),
                  self._path(dst_folder, name))

    def probe(self) -> None:
        """Fail loudly if the remote or the review folder is not usable.

        ``ensure_folders`` and ``list_files`` both swallow errors on purpose -
        mkdir on an existing folder is not news, and an empty folder and an
        unreachable one both list as nothing. That makes them useless as a
        health check, so this asks the one question that has a real answer:
        can we read the review folder at all?
        """
        self._run("lsf", f"{self.remote}:", "--max-depth", "1")

    def check(self) -> dict[str, Any]:
        """Is the remote reachable and what is waiting in each folder?"""
        result: dict[str, Any] = {
            "remote": self.remote,
            "review_folder_id": self.folder_id,
            "rclone": self.exe,
        }
        try:
            self.probe()
            self.ensure_folders()
            result["folders"] = {
                folder: self.list_files(folder) for folder in FOLDERS
            }
            result["ok"] = True
        except DriveError as exc:
            result["ok"] = False
            result["error"] = str(exc)
        return result


# --------------------------------------------------------------------------
# Caption sidecars
#
# The creative and the text that goes with it are uploaded as a pair, so the
# publish run - which may happen hours later, on a different machine, from a
# batch that no longer exists anywhere - still knows what to write under it.
# --------------------------------------------------------------------------

def sidecar_name(image_name: str) -> str:
    return str(Path(image_name).with_suffix(SIDECAR_SUFFIX))


def write_sidecar(path: Path, item: dict[str, Any], day: str) -> Path:
    path = Path(path)
    path.write_text(json.dumps({
        "date": day,
        "index": item["index"],
        "content_id": item["content_id"],
        "theme": item.get("theme"),
        "headline": item.get("headline"),
        "caption_facebook": item["caption_facebook"],
        "caption_instagram": item["caption_instagram"],
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_sidecar(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DriveError(f"Caption file {path} is unreadable: {exc}") from exc


def review_filename(day: str, index: int, content_id: str) -> str:
    """Sorts by date then position, and says what it is at a glance."""
    return f"{day}-{index:02d}-{content_id}.jpg"
