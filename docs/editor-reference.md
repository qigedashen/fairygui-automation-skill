# FairyGUI 编辑器速查

> 来源: https://fairygui.com/docs/editor/ （官方编辑器文档全量摘录的结构化速查版）

## 一、项目文件结构

```
项目根/
├── test.fairy           ← 项目标识文件（文件名即项目名）
├── assets/              ← 包内容放置目录
│   ├── Package1/        ← 每个包一个目录，目录名 = 包名
│   │   ├── package.xml  ← 包描述（二进制格式 ≥3.1.5）
│   │   ├── xxx.png      ← 导入的素材
│   │   └── ...
│   └── Package2/
├── assets_xx/           ← 分支内容放置目录（xx = 分支名）
├── settings/            ← 配置文件放置目录
└── .objs/               ← 内部数据目录（**不入版本库，不共享**）
```

**关键规则**：
- 项目路径**不要含中文**（官方明确要求）
- `.objs/` 是编辑器缓存，团队协作时每人本地独立
- 2.x 版本项目只能用"打开文件夹"方式打开

## 二、资源导出与可见性

每个资源有"是否导出"属性。已导出的资源在图标右下角有小红点。

| 属性 | 含义 |
|---|---|
| 导出 (exported=true) | 可被其他包引用，且可以用代码动态创建 |
| 不导出 (exported=false) | 包内部私有，不可被外部访问 |

**ofgui 补丁关键点**：`onPublishStart` 钩子在 `publishedResourceIds` 计算前执行，Lua 插件里改 `item.exported = true/false` 会直接改变最终发布集。

## 三、发布模式

### 编辑器原生发布
- 发布当前活跃包（默认）或全部包
- 仅发布定义：不重新生成纹理集（修改布局未改素材时加速）
- **必须勾选"使用二进制格式"**（≥3.0 SDK 已不支持 XML 格式）

### ofgui CLI 发布
```bash
node @openfairygui/cli/bin/cli.cjs publish <工程路径> -p <包名> -o <输出目录>
```
- ofgui 的图集打包算法与编辑器**不完全相同**
- atlas 数量和 PNG 大小可能不同 → 不是缺陷
- **关键校验**：`*_fui.bytes` 中的资源名集合是否完整

### 发布产物
```
PackageName_fui.bytes     ← 二进制包描述（定义文件）
PackageName_atlas0.png    ← 纹理图集
PackageName_atlas1.png
...
```

## 四、控制器与关联系统

### 控制器 (Controller)
- 编辑器设计，不建议代码创建
- 最常用：`selectedIndex` 切换页面
- 页面改变通知：`onChanged` 事件
- Gear 系统将控制器页面与元件属性（XY/Icon/Text/Size/Color/FontSize/Look/Display）绑定

### 关联系统 (Relations)
- 元件之间自动保持相对位置/尺寸
- 操作元件坐标时若想临时绕过，用"屏蔽关联系统"

## 五、字体

- FairyGUI 支持位图字体（BMFont）、动态字体、TMP 字体适配器
- 动态字体的 glyph 缓存会导致首次显示后可能突然变紫色然后恢复正常（参考字体文档）

## 六、常用快捷键

| 功能 | 快捷键 |
|---|---|
| 快速查找 | Ctrl+P |
| 显示关联查询 | 右键 → 查询依赖关系 |
| 组件组合 | Ctrl+G |
| 重命名 | F2 |
| 缩放舞台 | Ctrl+滚轮 / Ctrl + / Ctrl- |
| 恢复 100% | Ctrl+1 |
