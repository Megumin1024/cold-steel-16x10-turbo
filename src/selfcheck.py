"""只在临时模拟目录验证安装恢复，不访问用户游戏与存档。"""
from pathlib import Path
import json
import tempfile
from unittest.mock import patch


def run(app):
    passed = []
    with tempfile.TemporaryDirectory(prefix="cs16-check-", dir=Path.cwd()) as directory:
        root = Path(directory)
        fixture_exe, fixture_hbao = "离线测试程序".encode(), "离线测试原库".encode()

        def fixture(name, existing=False):
            game = root / name / "模拟游戏"
            game.mkdir(parents=True)
            (game / "ed8.exe").write_bytes(fixture_exe)
            (game / app.LOADER).write_bytes((app.PAYLOAD / app.LOADER).read_bytes() if existing else fixture_hbao)
            settings = root / name / "本地设置/settings.xml"
            settings.parent.mkdir()
            settings.write_bytes(b'<Settings><Resolution Width="1280" Height="720" /><ScreenMode>WINDOWED</ScreenMode><TurboMode>False</TurboMode><MSAA>8</MSAA></Settings>')
            if existing:
                (game / app.ORIGINAL).write_bytes(fixture_hbao)
                (game / "atmt_loader.ini").write_text('[Loader]\nEnabled=true\nModDir=atmt_mods\nMods=other.dll\n', encoding="utf-8")
            (game / "save.dat").write_bytes("不可变测试存档".encode())
            (game / "input.xml").write_bytes("不可变按键配置".encode())
            return game, settings

        def snapshot(game, settings):
            files = {p.relative_to(game).as_posix(): p.read_bytes() for p in game.rglob("*")
                     if p.is_file() and app.BACKUPS not in p.parts and p.name != app.RECORD}
            return files, settings.read_bytes()

        def refuses(call):
            try:
                call()
            except (ValueError, OSError):
                return
            raise AssertionError("预期拒绝却完成操作")

        with patch.object(app, "GAME_SHA", app.digest(fixture_exe)), patch.object(app, "ORIGINAL_SHA", app.digest(fixture_hbao)), patch.object(app, "closed", lambda: None):
            game, settings = fixture("完整恢复")
            old = snapshot(game, settings)
            app.install(game, settings, "2560x1600")
            assert b'Width="2560" Height="1600"' in settings.read_bytes()
            assert b"<MSAA>8</MSAA>" in settings.read_bytes()
            assert (game / "ed8.exe").read_bytes() == fixture_exe
            app.uninstall(game, settings)
            assert snapshot(game, settings) == old
            passed.append("新安装和卸载逐文件恢复；原程序、存档、键位和画质保持")
            app.install(game, settings, "1920x1200")
            refuses(lambda: app.install(game, settings, "1920x1200"))
            app.uninstall(game, settings)
            passed.append("卸载后重装与重复安装拒绝")

            game, settings = fixture("后续配置", existing=True)
            app.install(game, settings, "1280x800")
            loader = game / "atmt_loader.ini"
            loader.write_bytes(app.ini_key(loader.read_bytes(), "Loader", "Mods", "other.dll,deckscreen.dll,turbo_toggle.dll,later.dll") + b"; later comment\n")
            settings.write_bytes(settings.read_bytes().replace(b"<MSAA>8</MSAA>", b"<MSAA>4</MSAA>"))
            app.uninstall(game, settings)
            assert app.ini_key(loader.read_bytes(), "Loader", "Mods") == "other.dll,later.dll"
            assert b"; later comment" in loader.read_bytes()
            assert b"<MSAA>4</MSAA>" in settings.read_bytes()
            assert b'Width="1280" Height="720"' in settings.read_bytes()
            assert (game / app.LOADER).read_bytes() == (app.PAYLOAD / app.LOADER).read_bytes()
            passed.append("已有加载器的后续模块、注释与无关设置保留")

            game, settings = fixture("错误版本")
            (game / "ed8.exe").write_bytes("错误版本".encode())
            old = snapshot(game, settings)
            refuses(lambda: app.install(game, settings, "2560x1600"))
            assert snapshot(game, settings) == old and not (game / app.RECORD).exists()
            (game / "ed8.exe").write_bytes(fixture_exe)
            old = snapshot(game, settings)
            refuses(lambda: app.install(game, settings, "1920x1080"))
            assert snapshot(game, settings) == old and not (game / app.RECORD).exists()
            passed.append("错误版本与错误比例拒绝且不写入")

            game, settings = fixture("配置错误")
            settings.write_bytes(b"invalid xml")
            old = snapshot(game, settings)
            refuses(lambda: app.install(game, settings, "2560x1600"))
            assert snapshot(game, settings) == old and not (game / app.RECORD).exists()
            passed.append("缺失设置项在备份和安装前拒绝")

            game, settings = fixture("备份损坏")
            app.install(game, settings, "2560x1600")
            record = json.loads((game / app.RECORD).read_text(encoding="utf-8"))
            (game / app.BACKUPS / record["backup"] / "1.before").write_bytes("损坏".encode())
            old = snapshot(game, settings)
            refuses(lambda: app.uninstall(game, settings))
            assert snapshot(game, settings) == old
            passed.append("损坏备份在卸载预检时拒绝且不修改任何目标")

            game, settings = fixture("修改保护")
            app.install(game, settings, "2560x1600")
            (game / "atmt_mods/turbo_toggle.dll").write_bytes("用户改动".encode())
            old = snapshot(game, settings)
            refuses(lambda: app.uninstall(game, settings))
            assert snapshot(game, settings) == old
            passed.append("安装后被修改的 DLL 不删除不覆盖")

            game, settings = fixture("失败恢复")
            old = snapshot(game, settings)
            real_atomic = app.atomic
            failed = False

            def fail_once(path, data):
                nonlocal failed
                if path.name == "deckscreen.dll" and not failed:
                    failed = True
                    raise OSError("模拟写入失败")
                return real_atomic(path, data)

            with patch.object(app, "atomic", fail_once):
                refuses(lambda: app.install(game, settings, "2560x1600"))
            assert snapshot(game, settings) == old
            passed.append("安装中途写入失败自动恢复")

            game, settings = fixture("路径篡改")
            app.install(game, settings, "2560x1600")
            record_path = game / app.RECORD
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["files"][0]["name"] = "../../不允许"
            app.json_write(record_path, record)
            old = snapshot(game, settings)
            refuses(lambda: app.uninstall(game, settings))
            assert snapshot(game, settings) == old
            passed.append("安装记录路径越界拒绝")

            data = b"\xff\xfe" + '[Window.System]\r\nBorderless=false\r\n'.encode("utf-16-le")
            changed = app.ini_key(data, "Window.System", "Borderless", "true")
            assert changed.startswith(b"\xff\xfe") and app.ini_key(changed, "Window.System", "Borderless") == "true"
            assert app.ini_key(changed, "Window.System", "Borderless", "false") == data
            passed.append("UTF-16 LE 配置的 BOM 和换行保留")
            bad_payload = root / "损坏安装文件"
            bad_payload.mkdir()
            (bad_payload / "SHA256.json").write_text('{}', encoding="utf-8")
            with patch.object(app, "PAYLOAD", bad_payload):
                refuses(app.check_payload)
            passed.append("不完整安装文件清单拒绝")
    return {"version": app.VERSION, "通过数量": len(passed), "通过项目": passed,
            "边界": "全部使用临时模拟文件；不等同于游戏内测试"}
