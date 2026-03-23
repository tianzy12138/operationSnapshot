"""
数据模型定义

定义录制系统的核心数据结构：
- Action: 单个操作事件（鼠标移动、点击、滚轮、键盘按键）
- Recording: 录制记录，包含多个操作事件
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime
import json


@dataclass
class Action:
    """
    单个操作事件

    记录用户的一次操作，包括操作类型、时间戳和相关参数。

    Attributes:
        type: 操作类型
            - mouse_move: 鼠标移动
            - mouse_click: 鼠标点击
            - mouse_scroll: 鼠标滚轮
            - key_press: 键盘按键
        timestamp: 相对时间戳（秒），相对于录制开始时间
        x: 鼠标X坐标（鼠标操作时有效）
        y: 鼠标Y坐标（鼠标操作时有效）
        button: 鼠标按钮名称：left, right, middle（鼠标点击时有效）
        pressed: True表示按下，False表示释放（点击和按键时有效）
        key: 按键名称（键盘操作时有效）
        dx: 水平滚动量（滚轮操作时有效）
        dy: 垂直滚动量（滚轮操作时有效）
    """
    type: str
    timestamp: float
    x: Optional[int] = None
    y: Optional[int] = None
    button: Optional[str] = None
    pressed: Optional[bool] = None
    key: Optional[str] = None
    dx: Optional[int] = None
    dy: Optional[int] = None

    def to_dict(self) -> dict:
        """
        转换为字典

        只包含非None的字段，减小JSON文件大小。

        Returns:
            不包含None值的字典
        """
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> 'Action':
        """
        从字典创建Action对象

        Args:
            data: 包含操作数据的字典

        Returns:
            Action对象
        """
        return cls(**data)


@dataclass
class Recording:
    """
    录制记录

    包含一次录制的所有信息，包括名称、创建时间和操作列表。

    Attributes:
        name: 录制名称
        created_at: 创建时间（ISO格式字符串）
        total_duration: 总时长（秒）
        actions: 操作列表
    """
    name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_duration: float = 0.0
    actions: List[Action] = field(default_factory=list)

    @property
    def action_count(self) -> int:
        """获取操作数量"""
        return len(self.actions)

    def to_dict(self) -> dict:
        """
        转换为字典

        Returns:
            包含所有录制数据的字典
        """
        return {
            "name": self.name,
            "created_at": self.created_at,
            "total_duration": self.total_duration,
            "actions": [a.to_dict() for a in self.actions]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Recording':
        """
        从字典创建Recording对象

        Args:
            data: 包含录制数据的字典

        Returns:
            Recording对象
        """
        actions = [Action.from_dict(a) for a in data.get("actions", [])]
        return cls(
            name=data.get("name", "unnamed"),
            created_at=data.get("created_at", ""),
            total_duration=data.get("total_duration", 0.0),
            actions=actions
        )

    def to_json(self, filepath: str) -> None:
        """
        保存为JSON文件

        Args:
            filepath: 目标文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, filepath: str) -> 'Recording':
        """
        从JSON文件加载

        Args:
            filepath: JSON文件路径

        Returns:
            Recording对象
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def add_action(self, action: Action) -> None:
        """
        添加操作到录制

        同时更新总时长。

        Args:
            action: 要添加的操作
        """
        self.actions.append(action)
        if action.timestamp > self.total_duration:
            self.total_duration = action.timestamp
