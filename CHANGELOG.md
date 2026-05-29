
# Claude 桌面宠物 — 开发日志

> 项目路径：`E:\Program Files\ClaudeProject\Claude_DesktopPet`
> 技术栈：Python 3.14 + PyQt5 5.15
> 启动方式：双击 `start_pet.bat`

---

## 第一阶段：基础框架

### 核心功能
- 透明、置顶、无边框窗口（`FramelessWindowHint` + `WA_TranslucentBackground`）
- 单实例锁（`QSharedMemory`），防止重复启动
- 右键菜单 + 系统托盘
- 拖拽移动、边界钳制（重写 `move()` 方法）
- 状态机：IDLE / WALK / SLEEP / HAPPY / EAT

### 关键实现
- 30fps 动画循环（`QTimer` 33ms）
- 1.5s 行为评估循环（`QTimer` 1500ms）
- 桌面行走 + 边缘反弹（向量方向 + 钳制检测）

---

## 第二阶段：图标系统

### Claude 图标（C 形）
- 使用 lobehub SVG 路径数据，`QSvgRenderer` 渲染
- 径向渐变填充（#FF9E4A → #E8611A → #CC4400）
- 手绘圆眼（白色巩膜 + 深色瞳孔 + 高光 + 眨眼）
- 触角（摆动动画 + 圆球顶端）
- 圆角脚丫（走路弹跳）

### Claude Code 图标（终端形）
- lobehub SVG，线性渐变填充
- **原生 SVG 小孔作为眼睛**——不额外画眼，睁眼打孔、闭眼填平
- 无触角、无脚（保持几何感）
- 等宽字体 Zzz

### 切换机制
- `_icon_id = 0/1` 全局分发
- 所有绘制方法通过 `if self._icon_id == 0: ... else: ...` 分派
- 默认启动为 Claude Code 图标（`_icon_id = 1`）

---

## 第三阶段：交互功能

### 投喂爱心粒子
- 贝塞尔曲线绘制实心心形（单路径，无接缝）
- 6 个粒子从图标右上角出生，左上飘散
- 持续约 2s，大小不变，最后 10% 渐隐

### 空闲气泡
- emoji 气泡随机出现（💭 🎵 ❓ ✨ 😊 💤 👀 ✌️）
- `Segoe UI Emoji` 字体渲染
- 白色圆角气泡 + 尾尖指向桌宠
- 待机时 ~2%概率/帧触发，持续 4~6s

### 永久睡眠
- 点击"睡觉" → `_forced_sleep = True`，不会自动醒
- 菜单项变为"唤醒"
- 自动睡眠（低能量）不受影响

### Claude Code 启动
- 右键 `>_ Claude Code` 启动 claude.exe
- `CREATE_NEW_CONSOLE` 分配新终端窗口
- 工作目录设为 D:\

---

## 第四阶段：关键 Bug 修复

### Bug 1：不透明度泄漏
- **现象**：Zzz 的半透明效果"流"到后面的饥饿条
- **原因**：`p.setOpacity()` 在画完 Zzz 后没有恢复
- **修复**：在每个 `_draw_zs` 方法末尾加 `p.setOpacity(1.0)`

### Bug 2：气泡文字不一致
- **现象**：类常量 `_BUBBLE_TEXTS` 用 emoji，但 `_tick` 里却是旧版文本
- **原因**：硬编码残留，没使用类常量
- **修复**：`_tick` 改用 `random.choice(self._BUBBLE_TEXTS)`

### Bug 3：重启闪退
- **现象**：点重启直接卡死
- **原因**：`QApplication.quit()` 在 `menu.exec()` 内层事件循环中调用，无法正常退出
- **修复**：`QTimer.singleShot(0, ...)` + `os._exit(0)` 绕过 Qt 清理流程

### Bug 4：pyw 路径替换脆弱
- **现象**：如果 `sys.executable` 不包含 `python.exe`，替换会失败
- **修复**：改用 `os.path.splitext` + `'w.exe'`

### Bug 5：黑窗口（console）
- **现象**：桌宠启动自带 cmd 黑窗口
- **原因**：`python.exe` 是控制台程序，启动必有窗口
- **修复**：全部改用 `pythonw.exe`（纯 GUI 版本）

### Bug 6：Claude Code 启动无反应
- **现象**：点了没任何效果
- **原因**：GUI 进程的子进程无控制台可附着，claude.exe 启动后不可见
- **修复**：`subprocess.CREATE_NEW_CONSOLE` 强制分配新终端窗口

---

## 第五阶段：UI 优化

### 桌宠窗口圆角
- 多次尝试失败：`setClipPath`、`setMask`(QRegion/QBitmap/Polygon) 均因与 `WA_TranslucentBackground` 冲突无效
- **最终方案**：`DwmSetWindowAttribute(hwnd, 33, DWMWA_ROUND_PREFERENCE=2)` 直接调 Windows 11 DWM API

### 右键菜单圆角
- 初版用暗色主题，后改为白底 Mac 风格
- Windows 原生 QMenu 不支持 `border-radius`
- `Fusion` 风格 + `border-radius` 样式表 → 菜单内容可圆角，但框架仍是直角
- **最终方案**：创建 `RoundedMenu(QMenu)` 子类，在 `showEvent` 中对菜单的 HWND 也调 `DwmSetWindowAttribute`
- 三者缺一不可：保留原生框架 + DWM API 圆角 + Fusion 风格 + border-radius 样式表

---

## 技术笔记

### 模块结构（单文件 main.py，~740 行）
- 三个 SVG 常量（_CLAUDE_SVG / _CLAUDE_CODE_SVG / _CLAUDE_CODE_BODY）
- `PetWindow(QWidget)`：主体类，所有绘制和逻辑
- `RoundedMenu(QMenu)`：圆角菜单子类
- `_is_already_running()` + `main()`：入口

### 关键依赖
- PyQt5 (5.15.11)
  - QtCore: QTimer, QSharedMemory
  - QtGui: QPainter, QPainterPath, QFont, QPolygonF
  - QtSvg: QSvgRenderer
  - QtWidgets: QApplication, QWidget, QMenu, QSystemTrayIcon
- ctypes (Windows DWM API)
- subprocess / os

### 启动方式
```powershell
# 无控制台窗口启动
C:\...\pythonw.exe main.py
```

### 已知限制
- DWM 圆角仅 Windows 11 有效（Win10 忽略）
- Claude Code 启动路径硬编码为当前用户
- 不响应屏幕分辨率变化（需重启）
