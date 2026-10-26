# FairyGUI Unity API 类型索引速查

> 来源: https://fairygui.com/docs/api/ （241 公开类型 / 3022 成员）
> 这里只收录最常用的类型，完整列表查阅官方 API。

## 命名空间结构

| 命名空间 | 用途 |
|---|---|
| `FairyGUI` | 核心 UI 框架（控件、容器、包、舞台、控制器、动效等） |
| `FairyGUI.Utils` | 工具类（XML/HTML/UBB 解析、ByteBuffer、压缩） |

## 核心 UI 控件（GObject 子类）

| 类型 | 用途 |
|---|---|
| **GObject** | 基类，所有 UI 元件的共同父类 |
| GComponent | 容器组件，最重要的容器 |
| GList | 列表控件 |
| GTree | 树形控件 |
| GButton | 按钮 |
| GLabel | 标签（图文混合） |
| GTextField | 纯文本 |
| GRichTextField | 富文本（含图片/动画/表情） |
| GTextInput | 可输入文本框（支持表情输入） |
| GImage | 图片 |
| GLoader | 动态装载器（加载外部资源） |
| GLoader3D | 3D 内容装载器 |
| GGraph | 图形（简单图形/占位/替换） |
| GGroup | 高级组 |
| GMovieClip | 动画 |
| GProgressBar | 进度条 |
| GSlider | 拖动条 |
| GScrollBar | 滚动条 |
| GComboBox | 下拉框 |
| GRoot | 顶层组件（UI 显示列表根） |

## 包与工厂

| 类型 | 用途 |
|---|---|
| **UIPackage** | UI 包管理：AddPackage/RemovePackage/CreateObject/LoadAllAssets |
| UIObjectFactory | 对象工厂：自定义控件工厂 |
| PackageItem | 包内资源项（Type/owner/asset 等） |
| PackageItemType | 资源类型枚举（Image/Atlas/Component/Font/Sound...） |

## 舞台与容器

| 类型 | 用途 |
|---|---|
| **Stage** | 舞台：输入事件源头、排序管理、配置 |
| **GRoot** | 顶层根组件：AddChild/RemoveChild/soundVolume |
| **Container** | 内部容器：renderMode/renderCamera/fairyBatching |
| UIContentScaler | 屏幕自适应 |
| UIConfig | 全局配置（必须在任何 UI 构造前设置） |
| UIPanel | Unity GameObject 上的 UI 面板组件 |

## 控制器与关联

| 类型 | 用途 |
|---|---|
| **Controller** | 控制器（selectedIndex/onChanged） |
| Relations | 关联系统 |
| RelationType | 关联类型枚举 |
| GearXY/Icon/Text/Size/Color/FontSize/Look/Display | 齿轮：控制器页面 → 元件属性 |

## 事件与手势

| 类型 | 用途 |
|---|---|
| EventDispatcher | 事件分发基类 |
| EventListener | 具体事件监听 |
| EventContext | 事件上下文 |
| InputEvent | 输入事件 |
| LongPressGesture | 长按手势 |
| SwipeGesture | 滑动手势 |
| PinchGesture | 捏合手势 |
| RotationGesture | 旋转手势 |
| DragDropManager | 高级拖放 |

## 渲染与效果

| 类型 | 用途 |
|---|---|
| **DisplayObject** | Unity DisplayObject 桥（texture/material/shader） |
| **StageCamera** | UI 正交相机 |
| CaptureCamera | PaintMode 自动生成的相机 |
| BlendMode | 混合模式枚举 |
| BlurFilter / ColorFilter | 滤镜 |
| Transition | 动效（编辑器可视化设计） |
| GTween / GTweener | 代码 Tween 动画系统 |
| EaseType | 缓动类型枚举 |

## 字体

| 类型 | 用途 |
|---|---|
| BaseFont | 字体基类 |
| DynamicFont | 动态字体 |
| BitmapFont | 位图字体（BMFont 格式） |
| TMPFont | TextMeshPro 适配器 |
| FontManager | 字体管理 |

## 其他重要类型

| 类型 | 用途 |
|---|---|
| Window | 窗口基类（onInit/doShowAnimation/doHideAnimation） |
| PopupMenu | 弹出菜单 |
| GObjectPool | 对象池 |
| GPath / GPathPoint | 路径（动画路径） |
| ScrollPane | 滚动面板 |
| Image | 内部图片管理 |
| NTexture | Native 纹理封装 |
| Emoji | 表情定义 |
| DisplayObjectInfo | GameObject → UI 节点关联（需 FAIRYGUI_TEST 宏） |

## 完整 API 查阅

👉 https://fairygui.com/docs/api/

该页面包含 **241 公开类型** 和 **3022 个公开/受保护成员**，支持按类型名、成员名搜索，所有签名直接源自 FairyGUI-unity C# 源码 + XML 注释。
