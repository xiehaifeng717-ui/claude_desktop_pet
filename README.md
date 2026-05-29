# Claude 桌面宠物 🐾

一只生活在你的屏幕上的轻量级桌面宠物——Python + PyQt5 构建。

## 功能

- **双图标切换**：Claude（经典 C 标）和 Claude Code（终端风格）两种图标
- **独立动画**：每个图标有自己的眼睛、表情和行为逻辑
- **交互**：拖拽移动、右键菜单、投喂爱心、空闲 emoji 气泡
- **智能状态**：IDLE / WALK / SLEEP / HAPPY / EAT — 桌宠有自己的生活节奏
- **始终置顶**：不影响你工作的同时随时陪伴
- **单实例**：不会开出来一窝
- **一键启动 Claude Code**：右键菜单直接打开 Claude Code CLI（工作目录 D:\）

## 启动

```bash
cd Claude_DesktopPet
pip install PyQt5
pythonw main.py
```

或者双击 `start_pet.bat`。

## 操作

| 操作 | 效果 |
|------|------|
| 左键拖拽 | 移动桌宠 |
| 右键菜单 | 投喂 / 睡觉(唤醒) / 切换图标 / 启动 Claude Code / 重启 / 退出 |
| 系统托盘 | 右键托盘图标重置位置或退出 |

## 环境要求

- Python 3.10+
- PyQt5 5.15+
- Windows 11（DWM 圆角效果需要 Win11）

## 技术栈

- **Python 3.14** + **PyQt5** 界面与渲染
- **QSvgRenderer** 矢量图标渲染
- **Windows DWM API**（DwmSetWindowAttribute）原生圆角窗口和菜单
- **QPainterPath** 程序化心形绘制和动画

## 版权声明

- **Claude** 和 **Claude Code** 图标、名称及品牌归属 **Anthropic** 所有。
- 图标 SVG 数据来自 [lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)（Apache 2.0 许可）。
- 本项目仅供**个人学习和娱乐用途**，不涉及任何商业使用。

---

用 Python 和 PyQt5 构建。
