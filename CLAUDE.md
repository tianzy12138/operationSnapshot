## 项目概述

网页操作录制与回放工具，用于录制用户在内嵌浏览器中的键盘鼠标操作，并支持循环回放。

## 运行命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

## 架构

```
main.py          # 入口，调用 gui.main()
gui.py           # PySide6 GUI，包含内嵌浏览器(QWebEngineView)和控制面板
models.py        # 数据模型: Action(单个操作), Recording(录制记录)
recorder.py      # 录制器，使用pynput监听全局鼠标/键盘事件
player.py        # 回放器，使用pyautogui模拟操作，支持循环回放
```

### 核心流程

- **录制**: `Recorder` 使用 pynput 监听全局事件 → 生成 `Action` 对象 → 存入 `Recording` → 保存为 JSON
- **回放**: 加载 JSON → `Player` 使用 pyautogui 按时间戳还原操作

### 数据流

```
用户操作 → pynput监听 → Action(timestamp, type, x, y, key...) → Recording → JSON文件
                                                          ↓
JSON文件 → Recording → Player → pyautogui执行
```

## 热键

- F9: 开始/停止录制
- ESC: 停止回放

## 录制文件

- 存储目录: `./recordings/`
- 格式: JSON，包含 name, created_at, total_duration, actions[]
- 操作类型: mouse_move, mouse_click, mouse_scroll, key_press

## 浏览器数据

- Cookie/缓存目录: `./browser_data/`
- 使用 QWebEngineProfile 持久化登录状态