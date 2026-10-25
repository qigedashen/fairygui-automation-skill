# FairyGUI 自动化工具

> 作者：qigedashen
>
> 用户交流群：**QQ 2156013623**

基于 `@openfairygui/cli`（ofgui）的 FairyGUI UI 包无头发布工具，修复了 ofgui 与 FairyGUI 官方编辑器的两处行为差异，并让编辑器的 Lua 插件在 CLI 发布时真正执行。

## 功能

1. **裁剪规则修复（根可达闭包）**：ofgui 原生只判断"被任意组件引用即保留"，会把仅被不可达组件引用的图片打进包。本补丁改为「exported 根 + 沿组件引用可达闭包 + 字体/骨骼依赖」，与编辑器一致。

2. **Lua 插件执行**：ofgui 原生只支持 JS Codegen 插件，遇到 `plugins/<name>/main.lua` 直接跳过。本补丁用 fengari（纯 JS Lua 5.3）执行这些 Lua 插件，`App`/`CS`/`PluginPath`/`fprint`/`require` 与 `onPublishStart`/`onPublishEnd`/`onDestroy` 钩子均可用，Lua 侧 `item.exported = true` 会直接写回 ofgui 的 Resource。

典型应用：996Extend 插件的 ItemIcon 图标过滤（按 Item.lua/ItemEquip.lua 的 Looks 字段控制导出）能在 CLI 发布时生效。

## 目录结构

```
fairygui-automation-skill/
├── SKILL.md                  # 技能核心指令（Trae 技能格式）
├── README.md                 # 本文件
├── .gitignore
└── scripts/
    ├── patch_ofgui.py        # ofgui 补丁脚本（幂等）
    ├── lua-plugin-host.cjs   # fengari Lua 插件宿主
    └── publish.ps1           # 一键发布脚本
```

## 安装

### 方式一：Trae 技能市场上传

下载 `fairygui-automation.skill`（或本仓库打包），在 Trae「插件市场 → 技能 → 上传技能」选择该文件安装。

### 方式二：skills.sh 社区生态

```bash
npx skills add qigedashen/fairygui-automation-skill
```

### 方式三：手动复制

将本仓库内容复制到 Trae 全局技能目录：

- Windows：`%USERPROFILE%\.trae-cn\skills\fairygui-automation\`
- macOS/Linux：`~/.trae-cn/skills/fairygui-automation/`

## 前置依赖

在 ofgui 所在的同一 `node_modules` 根目录安装：

```bash
npm install @openfairygui/cli fengari fengari-interop
```

## 使用

### 打补丁

```powershell
python scripts\patch_ofgui.py <ofgui 的 node_modules 或 dist 路径>
```

输出：
- `patched` — 首次打补丁成功
- `skipped` — 已打过，跳过（幂等）
- `anchor-mismatch` — ofgui 版本可能已变，需核对补丁逻辑
- `WARN: 缺少 fengari / fengari-interop` — 装上后 Lua 插件才能跑

### 一键发布

```powershell
.\scripts\publish.ps1 -OfguiNodeModules <ofgui node_modules> -Package Bag -Output D:\publish\Bag
```

可选参数：
- `-Repo <仓库根>` — 指定 FGUI 工程所在仓库（默认当前目录）
- `-Project <FGUI工程路径>` — 默认 `<Repo>/9963d_rxjh_fgui_project`
- `-ItemConfigDir <目录>` — Item.lua/ItemEquip.lua 所在目录

### 插件运行时参数

996Extend 插件通过 `CS.UnityEngine.PlayerPrefs.GetString("Item_Path")` 读取配置路径。CLI 无 PlayerPrefs，宿主支持：

- 环境变量（优先）：`OFGUI_ITEM_PATH`、`OFGUI_ITEMEQUIP_PATH`
- 插件目录 JSON：`plugins/996Extend/ofgui-prefs.json`

## 验证

发布成功标志（日志）：

```
publish: [996Extend] ItemIcon: exported 2365 -> 1995
publish: [996Extend] onPublishStart handled by Lua
atlas: Packed N images into M atlas(es) for package "Bag".
```

## 注意事项

- ofgui 的图集打包算法与官方编辑器不完全相同，atlas 数量和 PNG 大小可能不同，这不是缺陷。
- 关键校验：`*_fui.bytes` 中应包含的资源名集合是否完整。
- `onPublishStart` 在发布集计算**之前**执行，因此改 `item.exported` 能真正改变最终发布集。

## 交流

有问题或建议，欢迎加入 QQ 交流群：**2156013623**

## License

MIT
