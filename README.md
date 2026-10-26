# 闪之轨迹1：16:10 画面适配与加速按键切换

适用于 **《英雄传说：闪之轨迹1》PC v1.6 的指定 `ed8.exe`**。提供无需安装 Python 的 Windows 图形安装工具，整合已实测的旧版 16:10 适配模块与独立加速切换模块。

[下载 v1.0.0 Windows 安装包](https://github.com/Megumin1024/cold-steel-16x10-turbo/releases/tag/v1.0.0)

## 功能

- 将游戏设置为所选 16:10 分辨率和无边框模式，适配探索画面并隐藏实时剧情的上下遮幅。
- 沿用游戏原来的加速键：按一下开启，松开后保持，再按一下关闭；长按不会反复切换。
- 保留现有加速键位和场景、战斗倍率；启用游戏原生 TurboMode。
- 安装前自动备份涉及的文件，提供卸载与未完成安装恢复。保留存档、键位、画质和 ReShade 文件。

**标题界面的原有黑条和预录视频保持原样。** 营地按钮放大、HUD 重排等后续实验改动不属于本次发布基线。

## 兼容范围

- Windows 10/11 x64；游戏本身是 x86，内置模块同为 x86。
- 只支持以下 SHA-256 的 `ed8.exe`，不同版本会停止安装：

```text
a0b4f4f58ce34def430ea83718415a4853dd4b931fb9b91d79afe73f56a1c4eb
```

- 原始 `GFSDK_SSAO_D3D11.win32.dll` 的 SHA-256 必须为：

```text
4aeaf975231c2a79c23f9a1dcbe3d4b2f3c030deb46e6e45ec92df3068484572
```

- 同时支持本包所带 ATMT 加载器的已有安装，但必须有匹配的 `.orig.dll`，`ModDir=atmt_mods`，且加载器已启用。
- 不声明支持 `ed8jp.exe`、其他游戏、其他版本或同时修改同一绘制/输入函数的补丁。仅版本号相同不足以证明兼容。

## 安装

1. 先用游戏启动器保存一次设置，然后正常退出游戏。
2. 下载 Release 中的 Windows ZIP，解压到普通目录。
3. 双击 `ColdSteel-16x10-Turbo-v1.0.0.exe`，选择包含 `ed8.exe` 的游戏目录。
4. 选择屏幕实际支持的 16:10 分辨率，例如 2560×1600 或 1920×1200，点击“安装并备份”。
5. 重新启动游戏。使用游戏自身绑定的加速键切换加速。需要调整倍率时使用游戏原有设置。

安装器读取当前 Windows 用户的 `%LOCALAPPDATA%\TrailsOfColdSteel1\settings.xml`，仅调整 Resolution、ScreenMode、TurboMode。若存在 `dxgi.ini`，只调整已有的六个窗口/拉伸相关键，保留其他内容和编码。不安装或配置 ReShade、Special K。

若游戏目录无写权限，请先将游戏放在当前用户可写的位置，或自行选择合适权限运行。本工具不自动提权。

## 卸载与恢复

退出游戏，再次运行安装工具，选择同一游戏目录并点击“卸载并恢复”。

- 安装记录位于游戏目录的 `cold-steel-16x10.install.json`。
- 原文件与记录存放在 `cold-steel-16x10-backups/日期时间_随机标识/`；卸载前也会保留当前文件快照。
- 不要删除或搬走这些记录和备份，否则自动恢复将无法可靠执行。
- 卸载仅恢复本次修改的设置项，保留后续无关画质改动；对于已有加载器，移除本次追加的模块名并保留后来加入的其他模块与注释。
- 如果受管理的 DLL、配置项、首次创建的加载器配置或备份被另行修改，工具会停止自动覆盖并说明冲突。请保留备份后手动处理，避免丢失后续改动。
- 未完成的安装可以用同一“卸载并恢复”入口恢复；已经卸载后可以重新安装。备份与空模块目录会保留。

## 验证情况

之前的本机测试中，用户已确认加速“正常切换，松开后保持”，且 2560×1600 下“探索和剧情均正常”。本次安装工具使用同一份旧版 `deckscreen.dll` 和同一份 `turbo_toggle.dll`，没有重新编译替换发布基线。

新安装器另有模拟目录中的安装/卸载、版本拒绝、配置保护、损坏备份、失败恢复等离线检查，以及打包后的 EXE 检查。详见 [验证记录](docs/验证记录.md)。这些检查不等于在所有机器、分辨率或全游戏场景下测试通过。战斗自动跳过同步仅有状态机测试，帧率影响尚未测量。

## 源码与构建

```powershell
python -m pip install -r requirements-build.txt
python src/installer.py self-test --report self-test.json
powershell -ExecutionPolicy Bypass -File build.ps1
```

推荐 Python 3.12。安装器源码在 `src/installer.py`，加速模块源码和状态机测试在 `src/turbo/`。`src/turbo/build.cmd` 使用 Visual Studio 2022 Build Tools 的 x86 C++ 编译器。

`payload/` 锁定发布用二进制与配置，并附 SHA-256 清单。`deckscreen.dll` 为之前实测的旧版定制二进制，本仓库暂未整理出可证明与该二进制对应的完整定制源码，因此不把后来改版源码当作它的对应源码。重建安装器会嵌入锁定的 DLL；不需要重建游戏模块。

## 来源与许可

- 加载器与 deckscreen 基于 [amadare42/atmt](https://github.com/amadare42/atmt)，参考固定提交 `c1bf5a0f3496001f9a5e98b241856cc08075444e`，组件为 loader 0.1.0 / deckscreen 0.1.1，并有本地定制。ATMT 的 MIT 许可原文见 [licenses/ATMT.txt](licenses/ATMT.txt)。
- 原生加速调用位置参考 [SenPatcher 固定提交的实现](https://github.com/AdmiralCurtiss/SenPatcher/blob/0681f42665cee0945d17c11f6dc41156b0a06a7c/native/sen1/exe_patch_turbo_mode.cpp)。本包使用独立输入模块，不分发 SenPatcher 程序。
- 本项目安装器与新增代码采用 MIT 许可，第三方组件保留各自版权。
- 不包含游戏本体、原始 HBAO 库、存档、账号信息或私人 ReShade 配置。游戏版权归原权利人所有。
