---
name: fairygui-automation
author: qigedashen
version: 1.0.0
description: FairyGUI UI 自动化发布工具，基于 @openfairygui/cli (ofgui) 实现无头发布，含裁剪规则与 Lua 插件执行两处补丁。用户要求发布 FairyGUI 包、运行编辑器 Lua 插件、修复 ofgui 与官方编辑器产物差异、或验证 ItemIcon 过滤等场景时使用。不要用于编辑器内可视化编辑或后端 Lua 业务脚本。
---

# FairyGUI 自动化工具

用 `@openfairygui/cli`（ofgui）在命令行发布 FairyGUI UI 包，并让官方编辑器的 Lua 插件（如 996Extend 的 ItemIcon 过滤）真正在 CLI 发布时生效。

## 背景与已落地修复

ofgui 原生发布器与 FairyGUI 官方编辑器有两处行为差异，已在本仓库固化补丁：

1. **裁剪规则**：ofgui 只判断"被任意组件引用即保留"，会把仅被不可达组件引用的图片打进包。补丁改为「exported 根 + 沿组件引用可达闭包 + 字体/骨骼依赖」，与编辑器一致。
2. **Lua 插件执行**：ofgui 原生只支持 JS Codegen 插件，遇到 `plugins/<name>/main.lua` 直接跳过。补丁用 fengari（纯 JS Lua 5.3）执行这些 Lua 插件，`App`/`CS`/`PluginPath`/`fprint`/`require` 与 `onPublishStart`/`onPublishEnd`/`onDestroy` 钩子均可用，Lua 侧 `item.exported = true` 会直接写回 ofgui 的 Resource。

## 关键文件

| 文件 | 作用 |
|---|---|
| `scripts/patch_ofgui.py` | 一次性把两处修复打进任意 ofgui 安装，可重复执行（已打过跳过）。**已随技能打包** |
| `scripts/lua-plugin-host.cjs` | fengari 实现的 Lua 插件宿主，补丁会复制进 ofgui 的 dist。**已随技能打包** |
| `scripts/publish.ps1` | 一键发布脚本：打补丁 → 设环境变量 → ofgui publish |
| `9963d_rxjh_fgui_project/plugins/996Extend/main.lua` | 项目的编辑器 Lua 插件入口（需项目自带） |
| `9963d_rxjh_fgui_project` | FGUI 工程根（含 `.fairy` 标识文件） |
| `client/.../FGUIExport/` | 官方编辑器产物目录，用于比对 |

## 标准工作流

### 1. 定位 ofgui 安装

```powershell
# 仓库内没有内置 ofgui，需指定 node_modules 或 dist 路径
# 常见：<持久化目录>\node_modules\@openfairygui\functions\dist
```

如果未安装，先装：
```powershell
npm install @openfairygui/cli fengari fengari-interop
```
`fengari` 与 `fengari-interop` 必须和 `@openfairygui/cli` 在**同一个 node_modules 根目录**。

### 2. 打补丁

```powershell
python <技能目录>\scripts\patch_ofgui.py <node_modules 或 dist 路径>
```

输出含义：
- `patched` — 该文件首次打补丁成功
- `skipped` — 已打过，跳过（幂等）
- `anchor-mismatch` — ofgui 版本可能已变，锚点不匹配，**不要继续**，需核对补丁逻辑
- `WARN: 缺少 fengari / fengari-interop` — 装上后 Lua 插件才能跑

### 3. 配置插件运行时参数

996Extend 插件通过 `CS.UnityEngine.PlayerPrefs.GetString("Item_Path")` 读取 Item 配置路径。CLI 没有 PlayerPrefs，宿主支持两种取值方式：

- 环境变量（优先）：`OFGUI_ITEM_PATH`、`OFGUI_ITEMEQUIP_PATH`（规则：`OFGUI_` + key 大写，非字母数字转 `_`）
- 插件目录 JSON：`plugins/996Extend/ofgui-prefs.json`

本项目的 Item 配置在：`client/.../Lua/game_config/Item.lua`、`ItemEquip.lua`。

### 4. 发布

```powershell
$env:OFGUI_ITEM_PATH = "<repo>\client\rjengineb_Data\StreamingAssets\Bundles\dev\Lua\game_config\Item"
$env:OFGUI_ITEMEQUIP_PATH = "<repo>\client\rjengineb_Data\StreamingAssets\Bundles\dev\Lua\game_config\ItemEquip"

node <ofgui>\node_modules\@openfairygui\cli\bin\cli.cjs publish <FGUI工程路径> -p <包名> -o <输出目录>
```

成功标志（日志）：
```
publish: [996Extend] ItemIcon: exported 2365 -> 1995
publish: [996Extend] onPublishStart handled by Lua
atlas: Packed N images into M atlas(es) for package "Bag".
```

## 验证方法

### 产物一致性
- 比对 `*_fui.bytes` 大小与 `*_atlas*.png` 数量/大小。ofgui 的图集打包算法与编辑器不完全相同，**atlas 数量和 PNG 大小可能不同**，这不是缺陷。
- 关键校验：`*_fui.bytes` 中应包含的资源名集合是否完整。用 Python 正则提取 `\d{6}` 名称并与预期集合比对，`missing_expected` 应为 0。

### 插件过滤结果
- 日志中的 `exported <before> -> <after>` 应与独立脚本（解析 package.xml + Item.lua/ItemEquip.lua 的 `Looks` 字段）算出的期望值一致。
- 本项目 ItemIcon 期望：1940 个命中图标 + 55 个非数字项 = 1995 exported。

### 钩子时序
`onPublishStart` 在 `publishedResourceIds` 计算**之前**执行，因此在钩子里改 `item.exported` 能真正改变最终发布集。

## 编码与路径注意事项

- **后端 Lua 是 GBK，前端 Lua 是 UTF-8**，不要混淆。本技能涉及的 ofgui 宿主（`*.cjs`）和补丁脚本（`*.py`）是 UTF-8。
- 仓库路径含 `[7.1.3版7.1.1资源]`，Python `open`/`os.walk` 原生支持；PowerShell 操作需用 `-LiteralPath` 避免 `[ ]` 被当通配符。
- 不要用 `Edit`/`Write` 工具直接改后端 Lua 文件，会破坏 GBK 编码。

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `module 'xxx' not found` | Lua 插件的 `require` 路径解析失败 | 检查 `PluginPath` 与宿主的 `resolveModule` 候选路径（插件目录/工程目录/上级目录） |
| `GetString` 拿到空串 | 点调用陷阱：fengari-interop 把第一个参数当 this | 宿主已兼容点/冒号调用；确认环境变量或 `ofgui-prefs.json` 已设 |
| `anchor-mismatch` | ofgui 升级后产物结构变化 | 对照 `patch_ofgui.py` 中的 `ANCHOR`/`OLD_A`/`OLD_C` 重新核对 |
| 发布集比编辑器多 | 根可达闭包补丁未生效 | 确认 `publish-*.js` 含 `collectRootReachableResourceIds` |
| Lua 插件未执行 | `node.js`/`node.cjs` 未打 Lua 补丁或缺 fengari | 确认含 `loadLuaPluginHost`，且同 node_modules 根有 fengari/fengari-interop |
