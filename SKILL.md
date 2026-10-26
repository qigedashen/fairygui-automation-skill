---
name: fairygui-automation
author: qigedashen
version: 1.1.0
description: FairyGUI UI 自动化发布工具，基于 @openfairygui/cli (ofgui) 实现无头发布，含裁剪规则与 Lua 插件执行两处补丁。
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
| `scripts/patch_ofgui.py` | 一次性把两处修复打进任意 ofgui 安装，可重复执行（已打过跳过） |
| `scripts/lua-plugin-host.cjs` | fengari 实现的 Lua 插件宿主，补丁会复制进 ofgui 的 dist |
| `scripts/publish.ps1` | 一键发布脚本：打补丁 -> 设环境变量 -> ofgui publish |
| `9963d_rxjh_fgui_project/plugins/996Extend/main.lua` | 项目的编辑器 Lua 插件入口（需项目自带） |
| `9963d_rxjh_fgui_project` | FGUI 工程根（含 `.fairy` 标识文件） |

## 标准工作流

### 1. 定位 ofgui 安装

```powershell
npm install @openfairygui/cli fengari fengari-interop
```
`fengari` 与 `fengari-interop` 必须和 `@openfairygui/cli` 在**同一个 node_modules 根目录**。

### 2. 打补丁

```powershell
python <skill_dir>\scripts\patch_ofgui.py <node_modules 或 dist 路径>
```

输出：`patched` / `skipped`（幂等）/ `anchor-mismatch`（ofgui 版本变了别继续）/ `WARN: 缺少 fengari`。

### 3. 配置插件运行时参数

996Extend 通过 `CS.UnityEngine.PlayerPrefs.GetString("Item_Path")` 读 Item 配置。宿主支持：
- 环境变量（优先）：`OFGUI_ITEM_PATH`、`OFGUI_ITEMEQUIP_PATH`（规则：`OFGUI_` + key 大写，非字母数字转 `_`）
- 插件目录 JSON：`plugins/996Extend/ofgui-prefs.json`

### 4. 发布

```powershell
$env:OFGUI_ITEM_PATH = "<repo>\client\rjengineb_Data\StreamingAssets\Bundles\dev\Lua\game_config\Item"
$env:OFGUI_ITEMEQUIP_PATH = "<repo>\client\rjengineb_Data\StreamingAssets\Bundles\dev\Lua\game_config\ItemEquip"

node <ofgui>\node_modules\@openfairygui\cli\bin\cli.cjs publish <FGUI工程路径> -p <包名> -o <输出目录>
```

成功标志：
```
publish: [996Extend] ItemIcon: exported 2365 -> 1995
publish: [996Extend] onPublishStart handled by Lua
atlas: Packed N images into M atlas(es) for package "Bag".
```

## 验证方法

- **产物一致性**：比对 `*_fui.bytes` 中资源名集合完整（atlas 数量和 PNG 大小可能不同，不是缺陷）。
- **插件过滤结果**：日志 `exported <before> -> <after>` 与独立脚本算出的期望值一致。
- **钩子时序**：`onPublishStart` 在 `publishedResourceIds` 计算**之前**执行，Lua 侧改 `item.exported` 能真正改变发布集。

## 编码与路径注意事项

- 后端 Lua GBK，前端 Lua UTF-8，不要混淆。本脚本 UTF-8。
- 路径含 `[]` 时 PowerShell 用 `-LiteralPath`。

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `module 'xxx' not found` | Lua 插件 `require` 路径解析失败 | 检查 `PluginPath` 与宿主 `resolveModule` 候选（插件目录/工程目录/上级目录） |
| `GetString` 拿到空串 | fengari-interop 把第一个参数当 this | 宿主已兼容点/冒号调用；确认环境变量或 `ofgui-prefs.json` 已设 |
| `anchor-mismatch` | ofgui 升级后产物结构变化 | 对照 `patch_ofgui.py` 的 `ANCHOR`/`OLD_A`/`OLD_C` 重新核对 |
| 发布集比编辑器多 | 根可达闭包补丁未生效 | 确认 `publish-*.js` 含 `collectRootReachableResourceIds` |
| Lua 插件未执行 | `node.js`/`node.cjs` 未打 Lua 补丁或缺 fengari | 确认含 `loadLuaPluginHost`，且同 node_modules 根有 fengari/fengari-interop |

---

## 官方参考文档索引（docs/）

| 本地文件 | 官方源 | 覆盖内容 |
|---|---|---|
| `docs/editor-reference.md` | https://fairygui.com/docs/editor/ | 编辑器项目结构、发布模式、导出规则、控制器/Gear、快捷键 |
| `docs/unity-sdk-reference.md` | https://fairygui.com/docs/unity/ + special/ | AddPackage 四种方式、UIPanel vs CreateObject、PaintMode、宏开关、DrawCall 优化、SDK 源码结构 |
| `docs/faq-troubleshooting.md` | https://fairygui.com/docs/faq/ | 官方 FAQ + ofgui/补丁特有问题 + 社区 7 条独有模式 |
| `docs/api-type-index.md` | https://fairygui.com/docs/api/ | 241 类型 3022 成员速查 |

补充链接：
- Unity SDK 仓库: https://github.com/fairygui/FairyGUI-unity （Unity 5.6+ / MIT / FairyBatching）
- 问题兜底社区: https://ask.layabox.com/?q=FairyGUI （Flarum，谷主本人回复）

## 场景 → 文档交叉引用

| 你要做的事 | 查哪里 |
|---|---|
| 首次配置 / 打补丁 / 发布 | 本 SKILL.md "标准工作流" |
| 理解 .fairy / assets / 包目录 | `docs/editor-reference.md` §一 |
| 选择 UIPanel vs CreateObject | `docs/unity-sdk-reference.md` §二 |
| AddPackage 四种方式 | `docs/unity-sdk-reference.md` §一 |
| FairyGUI-unity SDK 源码模块 | `docs/unity-sdk-reference.md` §七 |
| Unity 显示不正常（白屏/没图/错乱） | `docs/faq-troubleshooting.md` §二 |
| 包加载失败（invalid package / atlas not found） | `docs/faq-troubleshooting.md` §一 |
| DrawCall 太高 / 深度错乱 | `docs/faq-troubleshooting.md` §四 + `docs/unity-sdk-reference.md` §五 |
| 宏开关新功能 | `docs/unity-sdk-reference.md` §四 "平台宏" |
| Lua 插件在 ofgui 跑不起来 | 本 SKILL.md + `docs/faq-troubleshooting.md` §八 |
| Mac batchmode 闪退 | `docs/faq-troubleshooting.md` §九 |
| 查 API 参数 | `docs/api-type-index.md` -> https://fairygui.com/docs/api/ |
| 官方 FAQ 没覆盖 | `docs/faq-troubleshooting.md` §九 |
