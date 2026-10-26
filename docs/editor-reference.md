# FairyGUI 编辑器速查

> 来源: https://fairygui.com/docs/editor/ （结构化速查版）

## 一、项目文件结构

```
项目根/
├── test.fairy           ← 项目标识文件（文件名即项目名）
├── assets/              ← 包内容放置目录
│   ├── Package1/        ← 每个包一个目录，目录名 = 包名
│   │   ├── package.xml  ← 包描述（二进制格式 >=3.1.5）
│   │   └── xxx.png
│   └── Package2/
├── assets_xx/           ← 分支内容放置目录（xx = 分支名）
├── settings/            ← 配置文件放置目录
└── .objs/               ← 内部数据目录（**不入版本库，不共享**）
```

**规则**：项目路径**不要含中文**；2.x 版本项目只能用"打开文件夹"方式打开。

## 二、资源导出与可见性

每个资源有"是否导出"属性，已导出的图标右下角有小红点。

| 属性 | 含义 |
|---|---|
| 导出 (exported=true) | 可被其他包引用，可代码动态创建 |
| 不导出 (exported=false) | 包内部私有，不可外部访问 |

**ofgui 补丁关键点**：`onPublishStart` 钩子在 `publishedResourceIds` 计算**之前**执行，Lua 插件里改 `item.exported = true/false` 会直接改变发布集。

## 三、发布模式

### 编辑器原生
- 发布当前活跃包（默认）或全部包
- 仅发布定义：不改素材时加速
- **必须勾选"使用二进制格式"**（>=3.0 SDK 已不支持 XML 格式）

### ofgui CLI
```bash
node @openfairygui/cli/bin/cli.cjs publish <工程路径> -p <包名> -o <输出目录>
```
- atlas 数量 / PNG 大小可能与编辑器不同 -> **不是缺陷**
- 关键校验：`*_fui.bytes` 资源名集合完整

### 发布产物
```
PackageName_fui.bytes     ← 二进制包描述
PackageName_atlas0.png    ← 纹理图集
```

## 四、控制器与关联系统

- **Controller**：编辑器设计，不建议代码创建。常用：`selectedIndex` 切换页面，`onChanged` 通知。
- **Gear**：控制器页面 -> 元件属性（XY/Icon/Text/Size/Color/FontSize/Look/Display）绑定。
- **Relations**：元件间自动保持相对位置/尺寸。

## 五、常用快捷键

| 功能 | 快捷键 |
|---|---|
| 快速查找 | Ctrl+P |
| 组件组合 | Ctrl+G |
| 重命名 | F2 |
| 缩放舞台 | Ctrl+滚轮 / Ctrl +/- |
| 恢复 100% | Ctrl+1 |
