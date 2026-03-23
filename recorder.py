"""
操作录制模块

负责监听和记录用户的鼠标和键盘操作。
使用pynput库进行全局事件监听，记录操作类型、时间和参数。
"""
import time
import threading
from typing import Callable, Optional, List
from pynput import mouse, keyboard
from models import Action, Recording


class Recorder:
    """
    操作录制器

    使用pynput监听全局鼠标和键盘事件，将操作记录为Action对象列表。
    支持开始/停止录制，并通过回调通知操作计数更新。
    """

    def __init__(self):
        """初始化录制器"""
        self._is_recording = False       # 是否正在录制
        self._start_time: float = 0      # 录制开始时间
        self._actions: List[Action] = [] # 已录制的操作列表
        self._recording: Optional[Recording] = None  # 当前录制对象

        # 事件监听器
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None

        # 回调函数
        self._on_action: Optional[Callable[[int], None]] = None  # 操作计数回调

    @property
    def is_recording(self) -> bool:
        """是否正在录制"""
        return self._is_recording

    @property
    def action_count(self) -> int:
        """已录制的操作数量"""
        return len(self._actions)

    @property
    def recording(self) -> Optional[Recording]:
        """当前录制对象"""
        return self._recording

    def set_on_action(self, callback: Callable[[int], None]) -> None:
        """设置操作计数回调函数"""
        self._on_action = callback

    def start(self, name: str = "recording") -> None:
        """
        开始录制

        启动鼠标和键盘监听器，开始记录用户操作。

        Args:
            name: 录制名称，默认为"recording"
        """
        if self._is_recording:
            return

        self._is_recording = True
        self._start_time = time.time()
        self._actions.clear()
        self._recording = Recording(name=name)

        # 启动鼠标监听器
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self._mouse_listener.start()

        # 启动键盘监听器
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._keyboard_listener.start()

    def stop(self) -> Recording:
        """
        停止录制

        停止所有监听器，将操作添加到录制对象并返回。

        Returns:
            包含所有已录制操作的Recording对象
        """
        if not self._is_recording:
            return self._recording or Recording(name="empty")

        self._is_recording = False

        # 停止监听器
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

        # 将操作添加到录制对象
        if self._recording:
            for action in self._actions:
                self._recording.add_action(action)

        return self._recording

    def _get_timestamp(self) -> float:
        """获取相对时间戳（相对于录制开始时间）"""
        return round(time.time() - self._start_time, 3)

    def _notify_action(self) -> None:
        """通知操作计数更新"""
        if self._on_action:
            self._on_action(len(self._actions))

    def _on_mouse_move(self, x: int, y: int) -> None:
        """
        鼠标移动事件处理

        Args:
            x: 鼠标X坐标
            y: 鼠标Y坐标
        """
        if not self._is_recording:
            return

        action = Action(
            type="mouse_move",
            timestamp=self._get_timestamp(),
            x=x,
            y=y
        )
        self._actions.append(action)
        self._notify_action()

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """
        鼠标点击事件处理

        Args:
            x: 鼠标X坐标
            y: 鼠标Y坐标
            button: 鼠标按钮（左/右/中）
            pressed: True表示按下，False表示释放
        """
        if not self._is_recording:
            return

        action = Action(
            type="mouse_click",
            timestamp=self._get_timestamp(),
            x=x,
            y=y,
            button=button.name,
            pressed=pressed
        )
        self._actions.append(action)
        self._notify_action()

    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """
        鼠标滚轮事件处理

        Args:
            x: 鼠标X坐标
            y: 鼠标Y坐标
            dx: 水平滚动量
            dy: 垂直滚动量（正值向上，负值向下）
        """
        if not self._is_recording:
            return

        action = Action(
            type="mouse_scroll",
            timestamp=self._get_timestamp(),
            x=x,
            y=y,
            dx=dx,
            dy=dy
        )
        self._actions.append(action)
        self._notify_action()

    def _on_key_press(self, key) -> None:
        """
        键盘按下事件处理

        Args:
            key: 按下的键对象
        """
        if not self._is_recording:
            return

        # 跳过F9热键（用于开始/停止录制）
        if hasattr(key, 'name') and key.name == 'f9':
            return

        key_name = self._get_key_name(key)
        action = Action(
            type="key_press",
            timestamp=self._get_timestamp(),
            key=key_name,
            pressed=True
        )
        self._actions.append(action)
        self._notify_action()

    def _on_key_release(self, key) -> None:
        """
        键盘释放事件处理

        Args:
            key: 释放的键对象
        """
        if not self._is_recording:
            return

        # 跳过F9热键
        if hasattr(key, 'name') and key.name == 'f9':
            return

        key_name = self._get_key_name(key)
        action = Action(
            type="key_press",
            timestamp=self._get_timestamp(),
            key=key_name,
            pressed=False
        )
        self._actions.append(action)
        self._notify_action()

    def _get_key_name(self, key) -> str:
        """
        获取按键名称

        处理pynput不同类型的键对象，返回统一的键名字符串。

        Args:
            key: 键对象

        Returns:
            键名字符串
        """
        if hasattr(key, 'name'):
            # 特殊键（如shift, ctrl等）
            return key.name
        elif hasattr(key, 'char'):
            # 普通字符键
            return key.char
        else:
            # 其他情况
            return str(key)
