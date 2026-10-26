"""闪之轨迹1 v1.6：16:10 与加速切换安装工具。"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from uuid import uuid4

VERSION = "1.0.0"
GAME_SHA = "a0b4f4f58ce34def430ea83718415a4853dd4b931fb9b91d79afe73f56a1c4eb"
ORIGINAL_SHA = "4aeaf975231c2a79c23f9a1dcbe3d4b2f3c030deb46e6e45ec92df3068484572"
LOADER = "GFSDK_SSAO_D3D11.win32.dll"
ORIGINAL = "GFSDK_SSAO_D3D11.win32.orig.dll"
RECORD = "cold-steel-16x10.install.json"
BACKUPS = "cold-steel-16x10-backups"
MODULES = ["deckscreen.dll", "turbo_toggle.dll"]
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
PAYLOAD = BASE / "payload"
FILES = [LOADER, "atmt_mods/deckscreen.dll", "atmt_mods/deckscreen.ini",
         "atmt_mods/turbo_toggle.dll", "atmt_mods/turbo_toggle.ini"]
ALLOWED = set(FILES + [ORIGINAL, "atmt_loader.ini", "dxgi.ini", "@settings"])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe(path):
    """拒绝目录联接和符号链接，避免备份或恢复越过用户选择的路径。"""
    path = Path(os.path.abspath(path))
    for item in [path, *path.parents]:
        if item.exists() or item.is_symlink():
            require(not item.is_symlink() and not item.is_junction(), "路径含链接或联接：" + str(item))
    return path


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".cs16-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def json_write(path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"))


def closed():
    if os.name == "nt":
        result = subprocess.run(["tasklist.exe", "/FO", "CSV", "/NH"], capture_output=True,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        require(result.returncode == 0, "无法检查游戏进程，请关闭游戏后重试")
        require(not re.search(rb'(?im)^"ed8(?:jp)?\.exe"', result.stdout), "请先正常退出 ed8.exe / ed8jp.exe")


def default_settings():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "TrailsOfColdSteel1/settings.xml"


def decode_ini(data):
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16-le"), "utf-16-le", b"\xff\xfe"
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8"), "utf-8", b"\xef\xbb\xbf"
    return data.decode("utf-8"), "utf-8", b""


def ini_key(data, section, key, value=None):
    text, encoding, bom = decode_ini(data)
    sections = list(re.finditer(r"(?im)^\[" + re.escape(section) + r"\][ \t]*\r?\n(.*?)(?=^\[|\Z)", text, re.S))
    require(len(sections) == 1, "配置节缺失或重复：" + section)
    sec = sections[0]
    matches = list(re.finditer(r"(?im)^([ \t]*" + re.escape(key) + r"[ \t]*=[ \t]*)([^\r\n]*)", sec[1]))
    require(len(matches) == 1, "配置键缺失或重复：" + key)
    match = matches[0]
    if value is None:
        return match[2]
    start = sec.start(1) + match.start(2)
    end = sec.start(1) + match.end(2)
    return bom + (text[:start] + value + text[end:]).encode(encoding)


def xml_key(data, tag, value=None):
    pattern = rb"<" + tag.encode("ascii") + (rb"\b[^>]*?/>" if tag == "Resolution" else rb">[^<]*</" + tag.encode("ascii") + rb">")
    matches = list(re.finditer(pattern, data))
    require(len(matches) == 1, "设置项缺失或重复：" + tag)
    if value is None:
        return matches[0][0].decode("utf-8")
    return data[:matches[0].start()] + value.encode("utf-8") + data[matches[0].end():]


def check_payload():
    meta = json.loads((PAYLOAD / "SHA256.json").read_text(encoding="utf-8"))
    require(set(meta) == set(FILES), "安装文件清单不完整")
    for name in FILES:
        require(digest((PAYLOAD / name).read_bytes()) == meta[name], "安装文件校验失败：" + name)
    return meta


def file_path(game, settings, name):
    require(name in ALLOWED, "安装记录包含未知路径")
    return safe(settings if name == "@settings" else game / name)


def install(game, settings, resolution):
    game, settings = safe(game), safe(settings)
    closed()
    meta = check_payload()
    require((game / "ed8.exe").is_file() and digest((game / "ed8.exe").read_bytes()) == GAME_SHA,
            "游戏版本不匹配。仅支持 README 中指定 SHA-256 的《闪之轨迹1》PC v1.6 ed8.exe")
    width, height = map(int, resolution.lower().split("x"))
    require(640 <= width <= 7680 and 400 <= height <= 4800 and width * 10 == height * 16, "请选择有效的 16:10 分辨率")
    require(settings.is_file(), "未找到 settings.xml，请先运行游戏启动器保存设置")
    record_path = safe(game / RECORD)
    if record_path.exists():
        previous = json.loads(record_path.read_text(encoding="utf-8"))
        require(previous.get("state") in ["已卸载", "安装已回滚"], "已有安装记录，请先卸载或恢复未完成安装")
    current_loader = safe(game / LOADER)
    require(current_loader.is_file(), "游戏目录缺少 " + LOADER)
    loader_sha = digest(current_loader.read_bytes())
    require(loader_sha in [ORIGINAL_SHA, meta[LOADER]], "发现未知版本的 HBAO/ATMT 加载器，停止覆盖")
    fresh = loader_sha == ORIGINAL_SHA
    original = safe(game / ORIGINAL)
    if original.exists():
        require(digest(original.read_bytes()) == ORIGINAL_SHA, "已有原始 HBAO 副本版本不匹配")
    else:
        require(fresh, "已有 ATMT 加载器但缺少匹配的原始 HBAO 库")
    for name in FILES[1:]:
        path = safe(game / name)
        if path.exists():
            if path.suffix == ".dll":
                require(digest(path.read_bytes()) == meta[name], "已有不同版本的模块，停止覆盖：" + name)
    plan = []

    def add(name, data, kind="file", keys=None):
        path = file_path(game, settings, name)
        before = path.read_bytes() if path.exists() else None
        if before != data:
            plan.append({"name": name, "data": data, "old": before, "kind": kind, "keys": keys or []})

    if not original.exists():
        add(ORIGINAL, current_loader.read_bytes())
    for name in FILES:
        add(name, (PAYLOAD / name).read_bytes())
    loader_ini = safe(game / "atmt_loader.ini")
    added = []
    if loader_ini.exists():
        before = loader_ini.read_bytes()
        require(ini_key(before, "Loader", "ModDir").strip().lower() == "atmt_mods", "不支持自定义 ModDir，请先手动整理加载器")
        require(ini_key(before, "Loader", "Enabled").strip().lower() in ["true", "1"], "请先启用现有 ATMT 加载器")
        mods = [x.strip() for x in re.split("[,;]", ini_key(before, "Loader", "Mods")) if x.strip()]
        for name in MODULES:
            require(sum(x.lower() == name for x in mods) <= 1, "发现重复模块：" + name)
            if name not in [x.lower() for x in mods]:
                mods.append(name)
                added.append(name)
        if added:
            add("atmt_loader.ini", ini_key(before, "Loader", "Mods", ",".join(mods)), "loader", added)
    else:
        require(fresh, "现有 ATMT 安装缺少 atmt_loader.ini")
        add("atmt_loader.ini", b"[Loader]\r\nEnabled=true\r\nModDir=atmt_mods\r\nMods=deckscreen.dll,turbo_toggle.dll\r\nLogLevel=all\r\nLoadDelayMs=0\r\n")
    data = settings.read_bytes()
    keys = []
    for tag, value in [("Resolution", f'<Resolution Width="{width}" Height="{height}" />'),
                       ("ScreenMode", "<ScreenMode>BORDERLESS</ScreenMode>"),
                       ("TurboMode", "<TurboMode>True</TurboMode>")]:
        old = xml_key(data, tag)
        if old != value:
            keys.append([tag, old, value])
            data = xml_key(data, tag, value)
    add("@settings", data, "xml", keys)
    sk = safe(game / "dxgi.ini")
    if sk.exists():
        data, keys = sk.read_bytes(), []
        for section, key, value in [("Window.System", "Borderless", "true"), ("Window.System", "Fullscreen", "false"),
                                    ("Window.System", "OverrideRes", "0x0"), ("Display.Output", "ForceFullscreen", "false"),
                                    ("Display.Output", "ForceWindowed", "false"), ("Display.Output", "AspectRatioStretch", "false")]:
            try:
                old = ini_key(data, section, key)
            except ValueError:
                continue
            if old != value:
                keys.append([section, key, old, value])
                data = ini_key(data, section, key, value)
        add("dxgi.ini", data, "ini", keys)
    session = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_") + uuid4().hex[:8]
    backup = safe(game / BACKUPS / session)
    backup.mkdir(parents=True)
    entries = []
    for index, item in enumerate(plan):
        entry = {k: item[k] for k in ["name", "kind", "keys"]}
        entry.update(before=digest(item["old"]) if item["old"] is not None else None, after=digest(item["data"]))
        if item["old"] is not None:
            shutil.copy2(file_path(game, settings, item["name"]), backup / f"{index}.before")
        entries.append(entry)
    record = {"version": VERSION, "state": "正在安装", "game": str(game), "settings": str(settings),
              "backup": session, "fresh": fresh, "files": entries}
    json_write(backup / "record.json", record)
    json_write(record_path, record)
    try:
        for item in plan:
            path = file_path(game, settings, item["name"])
            require((path.read_bytes() if path.exists() else None) == item["old"], "安装前文件发生并发变化，停止：" + item["name"])
            atomic(path, item["data"])
        record["state"] = "已安装"
        json_write(record_path, record)
        json_write(backup / "record.json", record)
    except Exception:
        uninstall(game, settings)
        raise
    return "安装完成。重启游戏后生效；沿用游戏原加速键和倍率。\n备份：" + str(backup)


def uninstall(game, settings):
    game, settings = safe(game), safe(settings)
    closed()
    record_path = safe(game / RECORD)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    require(record.get("state") in ["已安装", "正在安装", "正在卸载"], "没有可恢复的安装记录")
    require(record.get("game") == str(game) and record.get("settings") == str(settings), "所选路径与安装记录不一致")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_[0-9a-f]{8}", record["backup"]), "备份路径无效")
    backup = safe(game / BACKUPS / record["backup"])
    entries = record["files"]
    require(len({x["name"] for x in entries}) == len(entries), "安装记录包含重复路径")
    plan = []
    for index, entry in enumerate(entries):
        path = file_path(game, settings, entry["name"])
        current = path.read_bytes() if path.exists() else None
        before = None
        if entry["before"] is not None:
            source = safe(backup / f"{index}.before")
            before = source.read_bytes()
            require(digest(before) == entry["before"], "备份校验失败，未修改任何文件")
        if current == before:
            continue
        if entry["kind"] in ["xml", "ini", "loader"] and before is not None and current is not None:
            restored = current
            if entry["kind"] == "loader":
                mods = [x.strip() for x in re.split("[,;]", ini_key(current, "Loader", "Mods")) if x.strip()]
                restored = ini_key(current, "Loader", "Mods", ",".join(x for x in mods if x.lower() not in entry["keys"]))
            else:
                for values in entry["keys"]:
                    args, old, new = values[:-2], values[-2], values[-1]
                    reader = xml_key if entry["kind"] == "xml" else ini_key
                    now = reader(restored, *args)
                    require(now in [old, new], "受管理配置已被修改，停止自动恢复：" + entry["name"])
                    if now == new:
                        restored = reader(restored, *args, old)
            before = restored
        else:
            require(current is not None and digest(current) == entry["after"], "安装后文件被修改，停止自动覆盖：" + entry["name"])
        plan.append((path, current, before))
    # 所有文件与备份预检通过后才开始卸载，允许失败后用原记录重试。
    record["state"] = "正在卸载"
    json_write(record_path, record)
    snapshot = safe(backup / ("卸载前_" + uuid4().hex[:8]))
    snapshot.mkdir()
    for index, (path, current, before) in enumerate(plan):
        require((path.read_bytes() if path.exists() else None) == current, "卸载前文件发生并发变化，停止：" + path.name)
        if current is not None:
            atomic(snapshot / f"{index}.bin", current)
        if before is None:
            path.unlink()
        else:
            atomic(path, before)
    record["state"] = "已卸载"
    json_write(record_path, record)
    json_write(backup / "record.json", record)
    return "卸载完成。安装前备份和卸载前快照均已保留。"


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    if os.name == "nt":
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root = tk.Tk()
    root.title("闪之轨迹1 · 16:10 与加速切换 v" + VERSION)
    root.geometry("660x410")
    root.minsize(660, 410)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="16:10 画面适配与加速按键切换", font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w")
    ttk.Label(frame, text="仅支持已验证的《闪之轨迹1》PC v1.6 ed8.exe", padding=(0, 8)).pack(anchor="w")
    ttk.Label(frame, text="游戏目录（包含 ed8.exe）").pack(anchor="w", pady=(10, 4))
    game_var = tk.StringVar()
    row = ttk.Frame(frame)
    row.pack(fill="x")
    ttk.Entry(row, textvariable=game_var).pack(side="left", fill="x", expand=True)
    ttk.Button(row, text="选择目录", command=lambda: game_var.set(filedialog.askdirectory() or game_var.get())).pack(side="left", padx=(8, 0))
    ttk.Label(frame, text="16:10 分辨率（应与屏幕支持的分辨率一致）").pack(anchor="w", pady=(16, 4))
    resolution = tk.StringVar(value="2560x1600")
    ttk.Combobox(frame, textvariable=resolution, values=["1280x800", "1440x900", "1680x1050", "1920x1200", "2560x1600", "2880x1800", "3840x2400"], state="readonly", width=22).pack(anchor="w")
    ttk.Label(frame, text="标题与预录视频保留原样；沿用原加速键和倍率。\n安装前请退出游戏。工具会备份将修改的文件，保留存档和画质设置。", padding=(0, 16)).pack(anchor="w")
    status = tk.StringVar(value="尚未执行安装或卸载")

    def act(action):
        try:
            require(bool(game_var.get()), "请先选择游戏目录")
            if not messagebox.askokcancel("确认操作", "将在所选游戏目录执行" + ("安装并备份。" if action == "install" else "卸载并恢复。") + "\n请确认游戏已关闭。", parent=root):
                return
            result = install(Path(game_var.get()), default_settings(), resolution.get()) if action == "install" else uninstall(Path(game_var.get()), default_settings())
            status.set("操作完成")
            messagebox.showinfo("操作完成", result, parent=root)
        except Exception as error:
            status.set("操作未完成，请查看错误说明")
            messagebox.showerror("操作未完成", str(error), parent=root)

    buttons = ttk.Frame(frame)
    buttons.pack(fill="x")
    ttk.Button(buttons, text="安装并备份", command=lambda: act("install")).pack(side="left")
    ttk.Button(buttons, text="卸载并恢复", command=lambda: act("uninstall")).pack(side="left", padx=12)
    ttk.Label(frame, textvariable=status, padding=(0, 12)).pack(anchor="w")
    if os.environ.get("CS16_GUI_SMOKE") == "1":
        root.after(2000, root.destroy)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=["install", "uninstall", "check", "self-test"])
    parser.add_argument("--game", type=Path)
    parser.add_argument("--settings", type=Path, default=default_settings())
    parser.add_argument("--resolution", default="2560x1600")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        if not args.action:
            gui()
        elif args.action == "check":
            result = {"version": VERSION, "payload": check_payload(), "status": "安装文件校验通过"}
            if args.report:
                json_write(args.report, result)
        elif args.action == "self-test":
            from selfcheck import run
            result = run(sys.modules[__name__])
            if args.report:
                json_write(args.report, result)
        else:
            require(args.game is not None, "请通过 --game 指定游戏目录")
            result = install(args.game, args.settings, args.resolution) if args.action == "install" else uninstall(args.game, args.settings)
            if args.report:
                json_write(args.report, {"status": result})
        return 0
    except Exception as error:
        if args.report:
            json_write(args.report, {"error": str(error)})
        if sys.stderr:
            print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
