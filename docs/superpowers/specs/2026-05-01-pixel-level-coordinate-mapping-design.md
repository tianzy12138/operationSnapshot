# 像素级控制 — 相对窗口坐标录制与回放设计

## 问题

当前录制使用 pynput 捕获绝对屏幕坐标，回放时用 pyautogui 直接还原。如果浏览器窗口在录制和回放之间移动了位置，鼠标操作会在错误的位置执行。

## 方案

录制时将绝对屏幕坐标转换为相对于浏览器窗口左上角的偏移量存储；回放时根据当前窗口位置还原为绝对坐标。

## 修改范围

### 1. models.py

- `Recording` 新增字段：
  - `window_width: Optional[int] = None` — 录制时浏览器窗口宽度
  - `window_height: Optional[int] = None` — 录制时浏览器窗口高度
- `Action` 的 `x`/`y` 语义变为相对浏览器窗口的偏移量
- 向后兼容：`window_width`/`window_height` 为 None 时视为旧格式（绝对坐标），不做转换

### 2. recorder.py

- `Recorder` 新增：
  - `_browser_rect_callback: Optional[Callable[[], Tuple[int, int, int, int]]]`
  - `set_browser_rect_callback(callback)` — 设置获取窗口位置的回调，返回 `(abs_x, abs_y, width, height)`
- `_on_mouse_move`、`_on_mouse_click`、`_on_mouse_scroll` 中：
  - 若回调存在，`rel_x = abs_x - browser_x`，`rel_y = abs_y - browser_y`
  - 存储转换后的相对坐标
- `stop()` 中：若回调存在，获取窗口尺寸写入 `Recording.window_width/height`

### 3. player.py

- `Player` 新增：
  - `_browser_rect_callback: Optional[Callable[[], Tuple[int, int, int, int]]]`
  - `set_browser_rect_callback(callback)` — 设置获取窗口位置的回调
- `_execute_action` 中：
  - 若回调存在且 action 有坐标，`abs_x = rel_x + browser_x`，`abs_y = rel_y + browser_y`
  - 用转换后的绝对坐标调用 pyautogui
- 若回调不存在（旧代码调用方式），行为不变

### 4. gui.py

- `RecorderApp` 新增 `_get_browser_rect()` 方法：
  ```python
  def _get_browser_rect(self) -> tuple:
      pos = self.browser.mapToGlobal(self.browser.rect().topLeft())
      return (pos.x(), pos.y(), self.browser.width(), self.browser.height())
  ```
- `_start_recording()` 中：`self.recorder.set_browser_rect_callback(self._get_browser_rect)`
- `_start_playback()` 中：`self.player.set_browser_rect_callback(self._get_browser_rect)`

## 数据流

```
录制:
  绝对屏幕坐标(pynput) → 减去窗口偏移 → 相对坐标 → Action.x/y → JSON

回放:
  JSON → Action.x/y(相对坐标) → 加上当前窗口偏移 → 绝对屏幕坐标 → pyautogui
```

## 向后兼容

- 旧录制文件没有 `window_width`/`window_height`，且 `x`/`y` 存的是绝对坐标
- 检测逻辑：`Recording` 中 `window_width is None` → 跳过坐标转换，直接使用存储的值
- 旧的 `Player` 调用方式（不设回调）也完全兼容

## 不涉及的部分

- 键盘事件无需修改（无坐标）
- 录制文件格式扩展仅为新增可选字段，不影响旧版本读取
