# FairyGUI 故障排查合并集

> 官方 FAQ: https://fairygui.com/docs/faq/
> 社区兜底: https://ask.layabox.com/?q=FairyGUI
> ofgui 补丁特有 + 社区 7 条独有模式

## 一、包加载与格式

### old package format
SDK >=3.0 不支持 XML 格式。发布对话框 -> 全局设置 -> 勾"使用二进制格式"。

### 包/组件对话框看不到
二进制 `xxx_fui.bytes` + 老版 SDK -> 升级到 3.0+。

### invalid package (换行符)
- 编辑器 <3.1.5: 关闭 Git autocrlf 重拉
- 编辑器 >=3.1.5: SDK <1.8.3 不认新二进制 -> **升级 SDK**（重要）
- 临时方案：把 `xxx.fairy` 里 `version="3.1"` 改成 `version="3"`
- Unity 项目路径含中文也会导致

### atlas not found / 白屏
```
FairyGUI: texture 'atlas0.png' not found in xxx
```
Unity 5.5+ 的 TextureShape 默认不是 2D -> 设为 2D。

## 二、运行时显示问题

### Create Component failed（编辑正常，运行失败）
1. UI 包没放 Resources（或拼错，超多新手踩）
2. 跨包引用没手动 AddPackage -> Awake 里补
3. 发布后改过文件名 -> 重设 UIPanel 的 Package/Component

### 显示不出图/字无报错
没放 `Resources/Shaders/` 着色器 -> 重新装插件。

### UI 重复 / 销毁后仍显示
场景里多相机勾了 UI 层：主相机 ClearFlags 不设 Depth，其他相机 Culling Mask 取消 UI。

### 层级错乱（FairyBatching）
代码改位置/旋转不自动调深度 -> `aObject.InvalidateBatchingState()`；Tween 过程中设 `invalidateBatchingEveryFrame = true`。

### 图片平铺有缝
双击图片 -> 属性 -> 勾"重复边缘像素"。

### 文字突然变紫恢复
动态字体 glyph 缓存。

## 三、PaintMode 相关

- CaptureCamera 自动生成，正常现象
- 必须定义 `VUI`(30) 和 `Hidden VUI`(31) Layer
- 自定义遮罩+PaintMode: `UIConfig.depthSupportForPaitingMode = true`

## 四、DrawCall 与性能

### Stage.LateUpdate CPU 高
这是事件源头，包含你的回调消耗。Deep Profiler 展开看具体哪个回调慢。FairyGUI 自身消耗在 Container.Update。

### DrawCall 仍高
**首先查 Unity Dynamic Batching 是否开启**。用 Frame Debugger 排查：遮罩、元件重叠、大段文本、平铺、滤镜、BlendMode。

### UI 包卸载后 Profiler 仍有 Asset
Unity 编辑器自身引用，真机不会。

## 五、声音与输入

### buttonSoundVolume 改了无效
只用于初始化。全局开关：
```csharp
GRoot.inst.EnabledSound();
GRoot.inst.DisableSound();
GRoot.inst.soundVolume = 0.5f;
```

### 长按事件
用 `LongPressGesture` 类。

### WebGL 中文输入
Scripting Define Symbols 加 `FAIRYGUI_WEBGL_TEXT_INPUT`。

### iOS 表情屏蔽
Xcode `Classes/UI/Keyboard.mm` -> `FILTER_EMOJIS_IOS_KEYBOARD` 改 0。

## 六、Lua 集成

### LuaException: Delegate FairyGUI.EventCallback1 not register
DelegateFactory 没 init。第三方框架问题，不是 FairyGUI。

### 支持哪个 Lua
tolua/slua/xlua/slxua 都可。参考 DCET: https://github.com/DukeChiang/DCET

## 七、其他

- **UGUI 共存**: 可以，"插入模型/粒子/Canvas"教程
- **播放视频**: Unity VideoPlayer，Texture 赋 Loader
- **代码动效**: GTween 或 DoTween
- **GTweener kill(false) 暂停其他**: 不要保存 GTweener 实例！
- **SRP Batcher 遮罩**: 升级 SDK >=4.2
- **Input System**: `FAIRYGUI_INPUT_SYSTEM` 宏
- **放 UI 到其他 Layer**: 源码版改 `StageCamera.cs` LayerName
- **UI 自动化测试**: `FAIRYGUI_TEST` + Poco-SDK Unity3D

---

## 八、ofgui / 补丁特有

| 现象 | 原因 | 处理 |
|---|---|---|
| `module 'xxx' not found` | Lua require 路径解析失败 | 检查 PluginPath / resolveModule 候选 |
| `GetString` 空串 | fengari-interop 点调用 this | 宿主已兼容点/冒号调用 |
| `anchor-mismatch` | ofgui 版本变了 | 对照 patch_ofgui.py 重核对 |
| 发布集比编辑器多 | 根可达闭包补丁未生效 | 确认含 `collectRootReachableResourceIds` |
| Lua 插件未执行 | node 适配器没打补丁或缺 fengari | 确认同 node_modules 根有 fengari |
| atlas 数量/大小不同 | 图集算法不同 | 不是缺陷 |

---

## 九、社区兜底 ask.layabox.com/?q=FairyGUI

Flarum 论坛，谷主（FairyGUI 作者本人）回复。

### 7 条社区高频模式

| 现象 | 严重度 | 结论 |
|---|---|---|
| Mac batchmode 闪退（AI 嵌入发布流程） | 高 | macOS Tahoe + M5 + Editor 6.1.4，Windows 正常。Mac 做无头发布先确认 |
| Android 特定机型合批随机漏绘 | 中 | FairyBatching + WebGL2 + Adreno 驱动 bug；Android 临时关 FairyBatching |
| 图集 + dds 压缩后部分不显示 | 中 | 跨版本纹理压缩管线兼容性 |
| BlendMode/滤镜 Runtime != 编辑器 | 中 | 谷主承认"天生差异"，真机反复验证 |
| 富文本运行时往上偏移 | 低 | 字体渲染基线不一致 |
| 关联底延展-底 target Y 变了显示错 | 低 | Relations 已知 bug |
| 图片字体新版不支持 | 低 | FairyGUI-layabox 仓库 bug |

### 社区入口

| 社区 | 地址 |
|---|---|
| FairyGUI 标签搜 | https://ask.layabox.com/?q=FairyGUI |
| Unity SDK Issues | https://github.com/fairygui/FairyGUI-unity/issues |
| 官方论坛 | https://www.fairygui.com 论坛 |
