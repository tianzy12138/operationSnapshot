"""
操作回放模块

负责读取录制文件并模拟执行鼠标和键盘操作。
支持循环回放、间隔设置和中途停止功能。
"""
import time
import threading
from typing import Callable, Optional
import pyautogui
import keyboard
from models import Recording, Action


class Player:
    """
    操作回放器

    读取Recording对象，按时间顺序模拟执行所有操作。
    支持设置循环次数和循环间隔，可通过ESC键或stop()方法中断回放。
    """

    def __init__(self):
        """初始化回放器"""
        self._is_playing = False      # 是否正在回放
        self._should_stop = False      # 停止信号
        self._remaining_loops: int = 0  # 剩余循环次数

        # 回调函数
        self._on_status: Optional[Callable[[str], None]] = None     # 状态更新回调
        self._on_remaining: Optional[Callable[[int], None]] = None  # 剩余次数回调

        # pyautogui 设置
        pyautogui.PAUSE = 0       # 操作间隔设为0，由程序自己控制时间
        pyautogui.FAILSAFE = True  # 启用安全机制（鼠标移到左上角可中止）

    @property
    def is_playing(self) -> bool:
        """是否正在回放"""
        return self._is_playing

    @property
    def remaining_loops(self) -> int:
        """剩余循环次数"""
        return self._remaining_loops

    def set_on_status(self, callback: Callable[[str], None]) -> None:
        """设置状态更新回调函数"""
        self._on_status = callback

    def set_on_remaining(self, callback: Callable[[int], None]) -> None:
        """设置剩余次数更新回调函数"""
        self._on_remaining = callback

    def play(self, recording: Recording, loops: int = 1, interval: float = 0.0) -> None:
        """
        同步回放录制

        Args:
            recording: 录制记录对象
            loops: 循环次数，默认1次
            interval: 循环间隔时间（秒），默认0秒
        """
        if self._is_playing:
            return

        self._is_playing = True
        self._should_stop = False
        self._remaining_loops = loops

        # 通知开始回放
        self._notify_status("回放中")
        self._notify_remaining(self._remaining_loops)

        # 循环回放
        while self._remaining_loops > 0 and not self._should_stop:
            self._notify_status(f"回放中 (剩余 {self._remaining_loops} 次)")
            self._play_actions(recording.actions)

            if self._should_stop:
                break

            # 更新剩余次数
            self._remaining_loops -= 1
            self._notify_remaining(self._remaining_loops)

            # 循环间隔等待
            if self._remaining_loops > 0 and interval > 0 and not self._should_stop:
                self._wait_with_check(interval)

        # 回放结束
        self._is_playing = False
        if self._remaining_loops == 0:
            self._notify_status("回放完成")
        else:
            self._notify_status("已停止")

    def play_async(self, recording: Recording, loops: int = 1, interval: float = 0.0) -> threading.Thread:
        """
        异步回放录制

        在后台线程中执行回放，不阻塞主线程。

        Args:
            recording: 录制记录对象
            loops: 循环次数
            interval: 循环间隔时间（秒）

        Returns:
            启动的线程对象
        """
        thread = threading.Thread(
            target=self.play,
            args=(recording, loops, interval),
            daemon=True  # 设置为守护线程，主程序退出时自动结束
        )
        thread.start()
        return thread

    def stop(self) -> None:
        """停止回放"""
        self._should_stop = True

    def _play_actions(self, actions: list) -> None:
        """
        回放操作列表

        按照时间戳顺序执行每个操作，保持原始时间间隔。

        Args:
            actions: Action对象列表
        """
        if not actions:
            return

        start_time = time.time()  # 记录开始时间

        for action in actions:
            if self._should_stop:
                break

            # 检查ESC键停止
            if keyboard.is_pressed('esc'):
                self._should_stop = True
                break

            # 计算并等待到目标时间
            target_time = start_time + action.timestamp
            current_time = time.time()
            if target_time > current_time:
                self._wait_with_check(target_time - current_time)

            if self._should_stop:
                break

            # 执行操作
            self._execute_action(action)

    def _execute_action(self, action: Action) -> None:
        """
        执行单个操作

        根据操作类型调用相应的pyautogui方法。

        Args:
            action: 要执行的操作对象
        """
        try:
            if action.type == "mouse_move":
                # 鼠标移动
                pyautogui.moveTo(action.x, action.y)

            elif action.type == "mouse_click":
                # 鼠标点击（按下或释放）
                button = action.button or "left"
                if action.pressed:
                    pyautogui.mouseDown(button=button, x=action.x, y=action.y)
                else:
                    pyautogui.mouseUp(button=button, x=action.x, y=action.y)

            elif action.type == "mouse_scroll":
                # 鼠标滚轮（pyautogui的scroll参数正向为向下滚动）
                pyautogui.scroll(action.dy or 0, action.x, action.y)

            elif action.type == "key_press":
                # 键盘按键（按下或释放）
                key = action.key
                if not key:
                    return

                # 特殊键映射（pynput按键名 -> pyautogui按键名）
                special_keys = {
                    'space': 'space',
                    'enter': 'enter',
                    'tab': 'tab',
                    'shift': 'shift',
                    'ctrl': 'ctrl',
                    'alt': 'alt',
                    'cmd': 'win',
                    'esc': 'esc',
                    'backspace': 'backspace',
                    'delete': 'delete',
                    'up': 'up',
                    'down': 'down',
                    'left': 'left',
                    'right': 'right',
                }

                if key.lower() in special_keys:
                    key = special_keys[key.lower()]

                if action.pressed:
                    pyautogui.keyDown(key)
                else:
                    pyautogui.keyUp(key)

        except Exception as e:
            print(f"执行操作失败: {e}")

    def _wait_with_check(self, duration: float) -> None:
        """
        等待指定时间，期间检查停止信号

        将等待时间分成小段，每段检查一次是否需要停止，
        以便能够快速响应停止请求。

        Args:
            duration: 等待时间（秒）
        """
        check_interval = 0.05  # 每50ms检查一次
        elapsed = 0
        while elapsed < duration and not self._should_stop:
            if keyboard.is_pressed('esc'):
                self._should_stop = True
                break
            sleep_time = min(check_interval, duration - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time

    def _notify_status(self, status: str) -> None:
        """通知状态更新"""
        if self._on_status:
            self._on_status(status)

    def _notify_remaining(self, remaining: int) -> None:
        """通知剩余次数更新"""
        if self._on_remaining:
            self._on_remaining(remaining)
