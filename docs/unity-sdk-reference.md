# FairyGUI Unity SDK 速查

> 来源: https://fairygui.com/docs/unity/ + https://github.com/fairygui/FairyGUI-unity
> FairyGUI-unity: Unity 5.6+ / MIT / 核心 FairyBatching DrawCall 优化

## 一、UI 包加载 (UIPackage.AddPackage)

### 四种方式

**1. Resources（最常用，自动排重）**
```csharp
UIPackage.AddPackage("demo");              // Resources/demo
UIPackage.AddPackage("subdir/demo");     // Resources/subdir/demo
UIPackage.AddPackage("Assets/SomePath"); // 仅 Editor
```

**2. 双 AssetBundle（热更推荐）**
把 `xxx_fui.bytes` 打为 desc_bundle，`xxx_atlas*.png` 打为 res_bundle：
```csharp
UIPackage.AddPackage(desc_bundle, res_bundle);
```
- 无排重检测，需自行保证只调用一次
- 优势：只改布局时只需推 desc_bundle，省流量

**3. 单 AssetBundle**
```csharp
UIPackage.AddPackage(bundle);
```

**4. 自定义（Addressable）**
```csharp
// 同步
UIPackage.AddPackage(assetPath, (name, ext, type, out dm) => {
    dm = DestroyMethod.Destroy;
    return res;
});
// 异步
UIPackage.AddPackage(descData, prefix, (name, ext, type, PackageItem item) => {
    someAsync(() => item.owner.SetItemAsset(item, res, DestroyMethod.Destroy));
});
```

### 包卸载与内存
```csharp
UIPackage.RemovePackage("name");     // 卸载整个包 + 资源
UIPackage.LoadAllAssets();           // 提前全载入
UIPackage.UnloadAssets();            // 只释放资源，保留包描述（UI 在但图空白）
UIPackage.ReloadAssets();            // 恢复资源（AB 载入需传新 bundle）
UIPackage.unloadBundleByFGUI = false;// 自行管理 AB
```
**建议**：常驻常用包，UI 内存可精确估算。

## 二、两种 UI 创建方式

### A. UIPanel（挂 GameObject）
```csharp
UIPanel panel = go.GetComponent<UIPanel>();
GComponent view = panel.ui;

// 动态创建
UIPanel panel = go.AddComponent<UIPanel>();
panel.packageName = "包名";
panel.componentName = "组件名";
panel.container.renderMode = RenderMode.WorldSpace;
panel.CreateUI();
```

| 属性 | 说明 |
|---|---|
| Render Mode | Screen Space Overlay / Camera / World Space |
| Sorting Order | 越大越靠前（1000 是 2D GRoot 层次） |
| Fairy Batching | 启用 DrawCall 合并 |
| Hit Test Mode | Default(高效) / Raycast(需 3D 交互) |
| Fit Screen | FitSize / FitWidthMiddle / FitHeightCenter |

**重要限制**：UIPanel 只存包名字符串，不引用纹理。跨包引用或 AB 包必须在 Awake 手动 AddPackage。

### B. CreateObject（代码动态创建）
```csharp
GComponent view = UIPackage.CreateObject("包名", "组件名").asCom;
GRoot.inst.AddChild(view);            // 方式 1
window.contentPane = view; window.Show(); // 方式 2
aComponent.AddChild(view);           // 方式 3

UIPackage.CreateObjectAsync("包", "组件", cb);  // 异步防卡顿
view.Dispose();                       // 必须手动销毁
```

**危险警告**：不要把 CreateObject 的对象挂到普通 GameObject！GameObject 销毁会顺带销毁 UI 内部 GameObject 导致空引用。

## 三、HUD（3D 头顶 UI）
```csharp
Stage.inst.SortWorldSpacePanelsByZOrder(100);
```
- 放在 3D 对象上的 UIPanel **无法与其他 UIPanel 合并 DC**
- 同屏多人物改用 2D UI + 坐标同步
- 需自行 LookAt 面向屏幕

## 四、特色功能与平台宏

### PaintMode（绘画模式）
```csharp
displayObject.EnterPaintingMode(1024, null);
// 渲染一帧后
RenderTexture tex = dObject.paintingGraphics.texture as RenderTexture;
displayObject.LeavePaintingMode(1024);
```
Unity 层必须定义 `VUI`(30) 和 `Hidden VUI`(31) Layer，且所有非 CaptureCamera **不选择**这两个层。

### 表情系统
```csharp
var emojies = new Dictionary<uint, Emoji>();
emojies.Add(0x1f600, new Emoji("ui://Emojies/1f600"));
richTextField.emojies = emojies;
```
手机键盘表情用 **UCS32**（4 字节 Unicode），C# 表示为 `"\U0001f600"`（Surrogate Pair）。

### 平台宏

| 宏 | 功能 |
|---|---|
| `FAIRYGUI_TEST` | UI 自动化测试 + DisplayObjectInfo（GameObject -> UI 节点） |
| `FAIRYGUI_INPUT_SYSTEM` | 切 Unity 新 Input System |
| `FAIRYGUI_WEBGL_TEXT_INPUT` | WebGL 中文输入 |
| `RTL_TEXT_SUPPORT` | 阿拉伯文从右向左（需源码版） |

### 其他
- SRP/URP: 支持，>=4.2 解决 SRP Batcher 遮罩问题
- Lua 框架: tolua/slua/xlua/slxua 均可（纯 C# 无第三方依赖）

## 五、DrawCall 优化

1. 开 FairyBatching（UIPanel 属性或 `GComponent.fairyBatching = true`）
2. Unity **Dynamic Batching 必须开启**
3. 避免：元件重叠、遮罩、大段文本、图片平铺、滤镜、BlendMode
4. 开了 FairyBatching 的组件，代码改位置/旋转不会自动调深度：
```csharp
aObject.InvalidateBatchingState();   // 任意子元件调用，每帧也可
```
5. Tween 深度错乱 -> `tween.invalidateBatchingEveryFrame = true`

## 六、声音控制

```csharp
GRoot.inst.EnabledSound();
GRoot.inst.DisableSound();
GRoot.inst.soundVolume = 0.5f;   // 全局（按钮 + 动效）
```

## 七、SDK 源码结构（GitHub fairygui/FairyGUI-unity）

> 来自 GitHub MCP `get_file_contents` 对 master 分支的探查

```
FairyGUI-unity/
├── README.md                    (Unity 5.6+ / MIT / FairyBatching)
├── Assets/
│   ├── Editor/                  (Unity Editor 工具)
│   ├── Examples/                (官方 Demo)
│   ├── Resources/               (默认着色器)
│   └── Scripts/                 (C# 源码主体)
└── .editorconfig / .gitattribute
```

### Assets/Scripts/ 模块划分

| 子目录 | 职责 |
|---|---|
| **Core/** | Stage, UIPackage, GObject, Controller, DisplayObject, UIConfig |
| **UI/** | GComponent, GList, GButton, GTextField, GRichTextField, GLoader... |
| **Event/** | EventDispatcher, EventListener, EventContext, InputEvent |
| **Gesture/** | LongPress, Swipe, Pinch, RotationGesture |
| **Filter/** | BlurFilter, ColorFilter |
| **Tween/** | GTween, GTweener, EaseManager |
| **Extensions/** | TMPFont, Puerts/XLua 桥接 |
| **Utils/** | XML/HTML/UBBParser, ByteBuffer, ZipReader |

所有 C# 编进 `FairyGUI.asmdef` 程序集（约 50+ 源文件，自动生成 API 注释）。

### 与 ofgui 的关系

FairyGUI-unity 是 Unity **运行时** SDK；ofgui 是独立 **CLI 发布器**，不依赖此仓库 C# 代码。两者通过产物格式（`xxx_fui.bytes` + atlas）对接。时序：ofgui 发布 -> 产物 -> Unity AddPackage 载入。

## 八、生命周期概览

```
启动 -> GRoot 自动创建
     -> AddPackage (Resources 自动排重，贴图/声音按需加载)
     -> 创建 UI
        -> UIPanel  (GameObject 自动生命周期)
        -> CreateObject (手动 Dispose)
```
