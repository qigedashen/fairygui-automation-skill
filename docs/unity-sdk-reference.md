# FairyGUI Unity SDK 速查

> 来源: https://fairygui.com/docs/unity/ 、 https://github.com/fairygui/FairyGUI-unity （Unity 接入与运行时关键 API 结构化速查）
> FairyGUI-unity 仓库: Unity 5.6+ 支持，MIT 许可证，核心特性 FairyBatching DrawCall 优化

## 一、UI 包加载 (UIPackage.AddPackage)

### 四种加载方式

#### 1. Resources 目录（最常用）
```csharp
// 自动排重：以传入路径为 key 检测
UIPackage.AddPackage("demo");            // Resources/demo
UIPackage.AddPackage("subdir/demo");     // Resources/subdir/demo
UIPackage.AddPackage("Assets/SomePath/Pkg"); // 仅 Editor 支持
```

#### 2. 双 AssetBundle（推荐用于热更）
将 `xxx_fui.bytes` 打包为 desc_bundle，`xxx_atlas*.png` 打包为 res_bundle：
```csharp
UIPackage.AddPackage(desc_bundle, res_bundle);
```
- **无排重检测**，需自行保证只调用一次
- 优势：只改布局时只需推送 desc_bundle，节省流量

#### 3. 单 AssetBundle
```csharp
UIPackage.AddPackage(bundle);
```
- 同样无排重检测

#### 4. 自定义加载（适用于 Addressable）
```csharp
// 同步
UIPackage.AddPackage(assetPath, (name, extension, type, out destroyMethod) => {
    destroyMethod = DestroyMethod.Destroy;
    return someLoadedResource;
});

// 异步（Addressable 等场景）
UIPackage.AddPackage(descData, assetNamePrefix, (name, extension, type, PackageItem item) => {
    // 异步完成后回调
    someAsyncCall(() => item.owner.SetItemAsset(item, res, DestroyMethod.Destroy));
});
```

### 包卸载与内存管理
```csharp
UIPackage.RemovePackage("packageName");    // 卸载整个包及所有资源
UIPackage.LoadAllAssets();                 // 提前全部载入（AddPackage 默认只在用到时才加载贴图/声音）
UIPackage.UnloadAssets();                  // 只释放资源，保留包描述（UI 仍在但图片空白）
UIPackage.ReloadAssets();                  // 恢复资源（从 AssetBundle 载入时需传入新 bundle）
UIPackage.unloadBundleByFGUI = false;     // 自行管理 AssetBundle，不让 FairyGUI 处理
```

> **不建议频繁 Load/Unload**：每次消耗 CPU + GC。建议常驻常用包，UI 内存可精确估算。

## 二、两种 UI 创建方式

### 方式 A：UIPanel（挂到 GameObject）

3 步使用：`GameObject > FairyGUI > UIPanel` → 选 Package/Component → Show。

```csharp
// 运行时获取 UI 引用
UIPanel panel = gameObject.GetComponent<UIPanel>();
GComponent view = panel.ui;

// 动态创建
UIPanel panel = go.AddComponent<UIPanel>();
panel.packageName = "包名";
panel.componentName = "组件名";
panel.container.renderMode = RenderMode.WorldSpace;
panel.container.fairyBatching = true;
panel.SetSortingOrder(1, true);
panel.CreateUI();
```

#### UIPanel 关键属性

| 属性 | 说明 |
|---|---|
| Render Mode | `Screen Space Overlay`(默认) / `Screen Space Camera` / `World Space` |
| Sorting Order | 越大越靠前（1000 是 2D UI 的 GRoot 层次） |
| Fairy Batching | 启用 DrawCall 合并 |
| Hit Test Mode | `Default`(内置射线，高效) / `Raycast`(自动创建 Collider，与 3D 交互时用) |
| Fit Screen | `Fit Size` 铺满 / `Fit Width And Set Middle` 横向铺满上下居中 / `Fit Height And Set Center` 纵向铺满左右居中 |
| Touch Disabled | 无交互 UI 可勾选以提升点击检测性能（如头顶血条） |

#### 重要限制
- UIPanel 只保存包名和组件名字符串，**不对纹理产生引用**
- 运行时自动载入仅限于 Resources 目录的包
- 引用到的其他包（跨包引用）或 AssetBundle 包 → 必须在 Awake 中用 `AddPackage` 手动载入
- UIPanel.Start 或首次访问 `.ui` 时创建 UI

### 方式 B：UIPackage.CreateObject（代码动态创建）

```csharp
GComponent view = UIPackage.CreateObject("包名", "组件名").asCom;

// 显示方式 1：加到 GRoot
GRoot.inst.AddChild(view);

// 显示方式 2：挂到 Window
aWindow.contentPane = view;
aWindow.Show();

// 显示方式 3：加到其他组件
aComponent.AddChild(view);

// 异步创建（大 UI 防卡顿）
UIPackage.CreateObjectAsync("包名", "组件名", (GObject obj) => { ... });

// 销毁（动态创建的必须手动 Dispose）
view.Dispose();
```

> **危险警告**：不要将 CreateObject 创建的对象挂到普通 GameObject 上！GameObject 销毁时会一并销毁 UI 的内部 GameObject，但 UI 还在使用 → 空引用。

## 三、HUD（3D 头顶 UI）

```csharp
// 排序：对 sortingOrder=100 的 UIPanel 按 z 排序，z 越小越靠前
Stage.inst.SortWorldSpacePanelsByZOrder(100);
```

- 放在 3D 对象上的 UIPanel **无法与其他 UIPanel 进行 DrawCall 合并**
- 同屏人物多时改用 2D UI 方案（与 3D 同步坐标）以合并 DC
- 需自行实现面向屏幕（LookAt）

## 四、特色功能与平台宏

### PaintMode（绘画模式）

让对象整体画到一张纹理上，支持滤镜、BlendMode ≠ Normal、倾斜、2D 模拟 3D 透视、曲面 UI。

```csharp
EnterPaintingMode(int requestorId, Margin? margin);
LeavePaintingMode(int requestorId);
// requestorId: 位标志（1, 2, 4, 8...），1024 以上用户自定义
// margin: 纹理四周留空
```

**Unity 层要求**：必须定义 `VUI`（默认 30）和 `Hidden VUI`（默认 31）两个 Layer，且所有相机（除自动的 CaptureCamera）**不要选择**这两个层。

### 组件截图
```csharp
dObject.EnterPaintingMode(1024, null);
yield return null;  // 必须等一帧
RenderTexture tex = (RenderTexture)dObject.paintingGraphics.texture.nativeTexture;
// ... 保存 ...
dObject.LeavePaintingMode(1024);
```

### 表情系统
```csharp
var emojies = new Dictionary<uint, Emoji>();
emojies.Add(0x1f600, new Emoji("ui://Emojies/1f600"));  // Unicode 表情
richTextField.emojies = emojies;
textInput.emojies = emojies;
```
- 自定义表情可用任意 Unicode；手机键盘表情用 **UCS32** 编码（4 字节 Unicode）
- C# 中用 `"\U0001f600"` 表示，Surrogate Pair 不能丢任何一个 char

### 平台宏（Scripting Define Symbols）

| 宏 | 功能 |
|---|---|
| `FAIRYGUI_TEST` | 启用 UI 自动化测试 + Scene GameObject → UI 节点关联（DisplayObjectInfo 组件） |
| `FAIRYGUI_INPUT_SYSTEM` | 切换到 Unity 新 Input System |
| `FAIRYGUI_WEBGL_TEXT_INPUT` | WebGL 平台中文输入支持 |
| `RTL_TEXT_SUPPORT` | 阿拉伯文（从右向左）显示（需源码版） |

### 其他平台支持
- **SRP/URP**：支持，需 SDK ≥ 4.2 以解决 SRP Batcher 下遮罩显示问题
- **Lua 框架**：tolua/slua/xlua/slxua 均可（FairyGUI 纯 C# 无第三方依赖）
- **AirTest 自动化**：定义 `FAIRYGUI_TEST` 后接入 Poco-SDK Unity3D 即可

## 五、DrawCall 优化关键

1. 开启 FairyBatching（UIPanel 属性或 GComponent.fairyBatching = true）
2. Unity 层面 **Dynamic Batching 必须开启**
3. 避免：不合理的元件重叠、过多遮罩（溢出隐藏/滚动）、大段文本、图片平铺、滤镜、BlendMode
4. 开了 FairyBatching 的组件，**代码 SetPosition 等不会自动触发深度调整**，需手动：
   ```csharp
   aObject.InvalidateBatchingState();
   // 可由任何子元件调用，每帧调用也没问题
   ```
5. Tween 过程中深度错乱 → `tween.invalidateBatchingEveryFrame = true`

## 六、声音控制

```csharp
// UIConfig.buttonSoundVolume 只用于初始化，后续改变无效

GRoot.inst.EnabledSound();       // 开声音
GRoot.inst.DisableSound();       // 关声音
GRoot.inst.soundVolume = 0.5f;   // 全局音量（按钮 + 动效）
```

## 七、SDK 源码结构（GitHub fairygui/FairyGUI-unity）

> 实际目录来自 GitHub MCP `get_file_contents` 对仓库 master 分支的探查

```
FairyGUI-unity/
├── README.md                    ← 项目说明（Unity 5.6+ / MIT / FairyBatching）
├── Assets/
│   ├── Editor/                  ← Unity Editor 工具、UIPanel 创建菜单
│   ├── Examples/                ← 官方 Demo UI 包 + 脚本
│   ├── Resources/               ← FairyGUI 默认着色器等
│   └── Scripts/                 ← C# 源码主体（见下）
├── images/                      ← README 配图
└── .editorconfig / .gitattribute
```

### Assets/Scripts/ 模块划分

| 子目录 | 职责 | 关键文件 |
|---|---|---|
| **Core/** | 核心类型：Stage、UIPackage、GObject、Controller、DisplayObject、UIConfig | BlendMode.cs、CaptureCamera.cs |
| **UI/** | 控件实现：GComponent、GList、GButton、GTextField、GRichTextField、GLoader、GScrollBar... | 241 类型的主体 |
| **Event/** | 事件分发系统：EventDispatcher、EventListener、EventContext、InputEvent | |
| **Gesture/** | 手势：LongPressGesture、SwipeGesture、PinchGesture、RotationGesture | |
| **Filter/** | 滤镜：BlurFilter、ColorFilter | |
| **Tween/** | 内置 Tween：GTween、GTweener、EaseManager | |
| **Extensions/** | 扩展：TMPFont（TextMeshPro 适配）、Puerts/XLua 桥接 | |
| **Utils/** | 工具：XML/HTML/UBBParser、ByteBuffer、ZipReader | |
| FairyGUI.asmdef | Assembly Definition，所有 C# 编进 `FairyGUI` 程序集 | |

> 完整 C# 文件约 **50+**，API 自动生成自这些源码的 XML 注释。改这个源码 → 重编译 DLL → 发布到 Unity 项目。

### 与 ofgui 的关系

FairyGUI-unity 是 Unity 端运行时 SDK。ofgui（@openfairygui/cli）是独立的 CLI 发布器，不依赖这个仓库的 C# 代码——它自己解析 `.fairy` 工程和 `package.xml` 然后生成二进制产物。两者通过**发布产物格式**（`xxx_fui.bytes` + `xxx_atlas*.png`）对接。

ofgui 补丁里的 `publishedResourceIds` / `collectRootReachableResourceIds` 是**发布时**在 ofgui 的 JS 里跑的；UIPackage 的 `AddPackage` 则是**运行时**在 Unity C# 里跑的。时序上：ofgui 发布 → 产物 → Unity AddPackage 载入。

## 八、生命周期概览

```
启动
  │
  ├── FairyGUI 自动创建 GRoot（顶层组件）
  ├── AddPackage（Resources 路径自动排重）
  │     │
  │     └── 包载入后贴图/声音 → 按需加载（AddPackage 不立即加载资源）
  │
  ├── 创建 UI
  │     ├── UIPanel（挂 GameObject，自动载入 Resources 包）
  │     │     └── Awake 中手动 AddPackage 跨包依赖
  │     └── CreateObject（动态创建，需手动 Dispose）
  │
  └── 销毁
        ├── UIPanel → GameObject 销毁时自动清理
        └── CreateObject → view.Dispose() 必须手动
```
