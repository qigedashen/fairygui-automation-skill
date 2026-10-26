# FairyGUI 故障排查合并集

> 来源: https://fairygui.com/docs/faq/ （官方 FAQ）+ ofgui/补丁特有问题 + 社区兜底
> 社区兜底: https://ask.layabox.com/ （Flarum 论坛，含 FairyGUI 标签）

## 一、包加载与格式

### 旧包格式警告
```
FairyGUI: old package format found in 'XXXX'
```
**原因**：编辑器导出 XML 格式，但 SDK ≥3.0 已不支持。
**解决**：发布对话框 → 全局设置 → 勾选"使用二进制格式"。

### 包/组件对话框看不到内容
**原因**：二进制格式包（`xxx_fui.bytes`）配老版 SDK。
**解决**：升级 SDK 到 3.0 以上。

### UI 包加载失败（换行符）
```
FairyGUI: invalid package 'XXXX',
if the files is checked out from git,
make sure to disable autocrlf option!
```
**原因 1（编辑器 <3.1.5）**：纯文本包描述被 Git autocrlf 改换行。
**解决**：关闭 Git autocrlf 后重拉。

**原因 2（编辑器 ≥3.1.5）**：SDK <1.8.3 无法识别新二进制描述。
**解决**：升级 SDK！升级 SDK！升级 SDK！
临时方案：把 `xxx.fairy` 里的 `version="3.1"` 改成 `version="3"`，编辑器会退回旧文本格式。

**原因 3**：Unity 项目路径含中文。
**解决**：改路径。

### atlas not found / 白屏
```
FairyGUI: texture 'atlas0.png' not found in xxx
```
**原因**：Unity 5.5+ 新增的 TextureShape 属性默认不是 2D。
**解决**：在 Unity 中把图集纹理的 TextureShape 设为 2D。

## 二、运行时显示问题

### Create Component 失败但编辑模式正常
```
Create Component1@Package1 failed!
```
**原因 1**：UI 包没放到 Resources 目录（或拼错了！超多新手踩）。
**原因 2**：跨包引用未手动 AddPackage → Awake 里补。
**原因 3**：发布后移动/改过文件名 → 重设 UIPanel 的 Package/Component。

### 显示不出图片/文字但无报错
**原因**：没放 FairyGUI 着色器（`Resources/Shaders/`）。
**解决**：重新装插件。

### UI 显示重复 / 销毁后仍在
**原因**：场景里有多个相机勾选了 UI 层。
**解决**：
1. 确保有主相机
2. 主相机 ClearFlags 不要设为 Depth
3. 其他相机 Culling Mask 取消 UI

### 层级显示错乱（FairyBatching 相关）
**原因**：开了 FairyBatching 的组件，代码调 SetPosition/旋转/缩放不触发深度重排。
**解决**：
```csharp
aObject.InvalidateBatchingState();  // 任意子元件调用都行
```
动效过程观察到错乱 → 设置 `invalidateBatchingEveryFrame = true`。

### 图片拼接/平铺有缝
**解决**：双击图片 → 属性对话框 → 勾选"重复边缘像素"。

### 突然文字变紫色然后恢复
**原因**：动态字体 glyph 缓存。参考字体文档。

## 三、PaintMode 相关

### 出现 CaptureCamera
**说明**：FairyGUI 自动生成的绘画模式相机，正常现象。

### 需要定义层警告
```
Please define two layers named 'VUI' and 'Hidden VUI' "
```
**解决**：Unity Layer 里加上 VUI(30) 和 Hidden VUI(31)，且所有非 CaptureCamera 都**不选择**这两个层。

### 自定义遮罩 + PaintMode 显示异常
```csharp
UIConfig.depthSupportForPaitingMode = true;
```

## 四、DrawCall 与性能

### Stage.LateUpdate CPU 高
- 这是事件源头，包含你的事件处理逻辑消耗
- Deep Profiler 展开 Stage.LateUpdate 看具体哪个回调慢
- FairyGUI 自身消耗在 Container.Update，非 Deep Profile 下很小

### DrawCall 仍高
1. **首先检查 Unity Dynamic Batching 是否开启**（必须开启）
2. 用 Frame Debugger 排查
3. 排查：遮罩过多、元件重叠、大段文本、图片平铺、滤镜、BlendMode

### UI 包卸载后 Profiler 仍显示 Asset
**说明**：Unity 编辑器自身引用。真机不会。

## 五、声音与输入

### buttonSoundVolume 改了无效
**原因**：`UIConfig.buttonSoundVolume` 只用于初始化。
**全局开关/音量**：
```csharp
GRoot.inst.EnabledSound();
GRoot.inst.DisableSound();
GRoot.inst.soundVolume = 0.5f;   // 含按钮 + 动效
```

### 长按事件
用 `LongPressGesture` 类，不是 Button 的事件。

### WebGL 中文输入
**Scripting Define Symbols** 加 `FAIRYGUI_WEBGL_TEXT_INPUT`。

### iOS 表情输入屏蔽
Xcode `Classes/UI/Keyboard.mm` → `FILTER_EMOJIS_IOS_KEYBOARD` 改 0。

## 六、Lua 集成

### LuaException: Delegate FairyGUI.EventCallback1 not register
**原因**：DelegateFactory 没 init。第三方框架的问题，不是 FairyGUI 本身。

### FairyGUI 支持哪个 Lua 框架
tolua/slua/xlua/slxua 都可以，FairyGUI 纯 C# 无第三方依赖。参考 DCET 框架：https://github.com/DukeChiang/DCET

## 七、其他

### FairyGUI 和 UGUI 共存
可以，参考教程"插入模型/粒子/Canvas"。

### 播放视频
Unity 原生 VideoPlayer，把 VideoTexture 赋给 Loader.texture。

### 代码创建动效 (Transition)
Transition 是编辑器可视化设计概念。全代码设计 → 直接用 GTween（内置）或 DoTween。

### Tweener kill(false) 导致其他动效暂停
**原因**：GTweener 是对象池重用的，不要保存 GTweener 实例！
**建议**：不要保存 GTweener，结束后不要 kill。

### SRP/URP 支持
- 支持
- SRP Batcher 下遮罩显示不正常 → 升级 SDK 到 ≥4.2

### Input System 支持
`FAIRYGUI_INPUT_SYSTEM` 宏切换。

### 放置 UI 到其他 Layer
用源码版本，改 `StageCamera.cs` 里的 `LayerName`。

### UI 自动化测试集成
定义 `FAIRYGUI_TEST` 宏 → 使用 AirTest Poco-SDK Unity3D。

---

## 八、ofgui / 补丁特有故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `module 'xxx' not found` | Lua 插件 `require` 路径解析失败 | 检查 `PluginPath` 与宿主 `resolveModule` 候选（插件目录/工程目录/上级目录） |
| `GetString` 拿到空串 | 点调用陷阱：fengari-interop 把第一个参数当 this | 宿主已兼容点/冒号调用；确认环境变量或 `ofgui-prefs.json` 已设 |
| `anchor-mismatch` | ofgui 升级后产物结构变化 | 对照 `patch_ofgui.py` 的 `ANCHOR`/`OLD_A`/`OLD_C` 重新核对 |
| 发布集比编辑器多 | 根可达闭包补丁未生效 | 确认 `publish-*.js` 含 `collectRootReachableResourceIds` |
| Lua 插件未执行 | `node.js`/`node.cjs` 未打 Lua 补丁或缺 fengari | 确认含 `loadLuaPluginHost`，且同 node_modules 根有 fengari/fengari-interop |
| PNG 数量/大小与编辑器不同 | ofgui 图集打包算法不同 | **不是缺陷**，关键是资源名集合完整 |

---

## 九、社区兜底

### LayaAir 社区（ask.layabox.com）

虽然 ask.layabox.com 是 LayaAir 官方社区，但 FairyGUI 有独立标签，且谷主（FairyGUI 作者）本人也在里面回复。搜索 URL：
- 综合搜索: https://ask.layabox.com/?q=FairyGUI
- 标签浏览: https://ask.layabox.com/tags → 搜 "fairyGUI" 标签

### 社区高频故障模式（抓取自 ask.layabox.com FairyGUI 标签帖）

| 现象 | 讨论帖 | 核心结论 |
|---|---|---|
| **Mac batchmode 闪退**（AI 自动化嵌入 FairyGUI 发布工作流） | 44 条回复，BUG 反馈 | macOS Tahoe + M5 Pro + FairyGUI Editor 6.1.4 batchmode 闪退；Windows 一切正常。谷主已跟进。**若在 Mac 做无头发布，先确认是否踩此坑** |
| **Android 特定机型合批随机漏绘**（筹码金色底图消失） | H5 + FairyGUI WebGL2 + Adreno 710 | 疑似 FairyBatching + WebGL2 + Adreno 驱动 bug；解决方案：在 Android 上临时关 FairyBatching 或降低合批粒度 |
| **编辑器导出图集 + LayaAir 纹理压缩后部分不显示** | 11 条回复，升级 Laya 3.4 beta1 后出现 | PNG 图集正常，开 .dds 压缩后部分丢失；跨版本升级时需注意纹理压缩管线兼容性 |
| **BlendMode / 滤镜在 Runtime 和编辑器效果差异** | 谷主官方承认 | FairyGUI 编辑器与 Runtime 的 BlendMode/滤镜效果天生有差异，"正常现象"。滤镜/BlendMode 需真机反复验证 |
| **富文本在运行时往上偏移** | 多帖复现 | 富文本字体渲染基线不一致。统一用编辑器设计后真机验证，不要信编辑器预览 |
| **关联底延展-底 在 target Y 变化后显示错误** | BUG 反馈 33 条回复 | Relations 关联系统在 target 元件 Y 动态变化时计算错误，官方已知问题 |
| **图片字体（BMFont）在新版不支持** | FairyGUI-layabox 仓库 bug | GitHub fairygui/FairyGUI-layabox 最新版图片字体路径有问题 |

### 其他社区入口

| 社区 | 地址 | 说明 |
|---|---|---|
| GitHub Issues | https://github.com/fairygui/FairyGUI-unity/issues | Unity SDK 官方 issue，提 BUG 需附重现项目 |
| FairyGUI 官方社区 | https://www.fairygui.com 论坛 | FairyGUI 原生社区（LayaAir 社区是同一批开发者但侧重不同引擎） |
| Gitee 镜像 | 国内加速 | 搜索 "FairyGUI-unity Gitee" 即可 |
| 编辑器 batchmode 文档 | FairyGUI 官方文档待补 | 当前 batchmode 无头发布文档不够全，Mac 闪退只能靠社区和谷主 |
