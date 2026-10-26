# FairyGUI Unity API 类型索引速查

> 来源: https://fairygui.com/docs/api/ （241 公开类型 / 3022 成员）

## 命名空间

| 命名空间 | 用途 |
|---|---|
| `FairyGUI` | 核心 UI 框架 |
| `FairyGUI.Utils` | 工具（XML/HTML/UBB、ByteBuffer） |

## 核心控件（GObject 子类）

| 类型 | 用途 |
|---|---|
| GObject | 基类 |
| GComponent | 容器组件 |
| GList | 列表 |
| GTree | 树 |
| GButton | 按钮 |
| GLabel | 标签 |
| GTextField | 纯文本 |
| GRichTextField | 富文本（图/动画/表情） |
| GTextInput | 可输入（支持表情） |
| GImage | 图片 |
| GLoader | 动态装载器 |
| GLoader3D | 3D 装载器 |
| GGraph | 图形/占位/替换 |
| GGroup | 高级组 |
| GMovieClip | 动画 |
| GProgressBar | 进度条 |
| GSlider | 拖动条 |
| GScrollBar | 滚动条 |
| GComboBox | 下拉框 |
| GRoot | 顶层根组件 |

## 包与工厂

| 类型 | 用途 |
|---|---|
| **UIPackage** | AddPackage/RemovePackage/CreateObject/LoadAllAssets |
| UIObjectFactory | 自定义控件工厂 |
| PackageItem | 包资源项 |
| PackageItemType | 资源类型枚举 |

## 舞台与容器

| 类型 | 用途 |
|---|---|
| **Stage** | 舞台/事件源/排序 |
| **GRoot** | 顶层根：AddChild/soundVolume |
| Container | renderMode/renderCamera/fairyBatching |
| UIContentScaler | 屏幕自适应 |
| UIConfig | 全局配置 |
| UIPanel | Unity GameObject 面板组件 |

## 控制器与关联

| 类型 | 用途 |
|---|---|
| **Controller** | selectedIndex/onChanged |
| Relations | 关联系统 |
| GearXY/Icon/Text/Size/Color/FontSize/Look/Display | 齿轮 |

## 事件与手势

| 类型 | 用途 |
|---|---|
| EventDispatcher | 事件分发基类 |
| EventListener / EventContext | 监听/上下文 |
| LongPressGesture | 长按 |
| SwipeGesture | 滑动 |
| PinchGesture | 捏合 |
| RotationGesture | 旋转 |
| DragDropManager | 高级拖放 |

## 渲染与效果

| 类型 | 用途 |
|---|---|
| **DisplayObject** | Unity 桥（texture/material） |
| **StageCamera** | UI 正交相机 |
| BlendMode | 混合模式枚举 |
| BlurFilter / ColorFilter | 滤镜 |
| Transition | 动效（编辑器设计） |
| GTween / GTweener | 代码 Tween |
| EaseType | 缓动枚举 |

## 其他

| 类型 | 用途 |
|---|---|
| Window | 窗口基类（onInit/doShow/doHide） |
| PopupMenu | 弹出菜单 |
| GObjectPool | 对象池 |
| GPath | 路径 |
| Emoji | 表情定义 |
| DisplayObjectInfo | GameObject -> UI 节点（需 FAIRYGUI_TEST 宏） |

## 完整 API

👉 https://fairygui.com/docs/api/

241 类型 / 3022 成员，源自 FairyGUI-unity C# 源码 + XML 注释。
