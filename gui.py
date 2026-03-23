"""
图形界面模块 - PySide6 版本

提供网页操作录制与回放工具的图形用户界面，包含：
- 内嵌浏览器窗口
- 录制控制面板
- 回放控制面板
- 文件管理功能
"""
import os
import json
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QDoubleSpinBox,
    QListWidget, QListWidgetItem, QGroupBox, QMessageBox,
    QFileDialog, QSplitter, QInputDialog
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PySide6.QtCore import Qt, QUrl, Signal

from recorder import Recorder
from player import Player
from models import Recording


class BrowserContainer(QWidget):
    """浏览器容器 - 保持16:9比例显示"""

    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)

    def resizeEvent(self, event):
        """重设大小时保持16:9比例"""
        width = event.size().width()
        # 计算高度 (宽度 / 16 * 9)
        height = int(width * 9 / 16)
        # 设置浏览器大小
        self.browser.setFixedSize(width, height)
        super().resizeEvent(event)


class RecorderApp(QMainWindow):
    """
    录制应用主类

    提供完整的GUI界面，包含录制、回放、文件管理和浏览器功能。
    使用Signal机制处理跨线程UI更新。
    """

    # 定义信号用于跨线程更新UI
    remaining_signal = Signal(int)  # 剩余循环次数更新信号
    status_signal = Signal(str)      # 回放状态更新信号

    GAME_URL = "https://gamer.qq.com/v2/game/96897"  # 默认游戏URL
    RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), "recordings")  # 录制文件存储目录

    def __init__(self):
        """初始化应用"""
        super().__init__()

        self.setWindowTitle("网页操作录制与回放工具")
        self.setGeometry(100, 100, 1200, 700)
        self.setFixedSize(1200, 500)  # 固定窗口大小

        # 确保录制目录存在
        os.makedirs(self.RECORDINGS_DIR, exist_ok=True)

        # 初始化核心组件
        self.recorder = Recorder()  # 录制器
        self.player = Player()      # 回放器

        # 状态变量
        self._current_recording: Optional[Recording] = None  # 当前录制对象
        self._selected_file: Optional[str] = None            # 当前选中的录制文件

        # 设置回调函数
        self.recorder.set_on_action(self._on_action_recorded)
        self.player.set_on_status(self._on_play_status)
        self.player.set_on_remaining(self._on_play_remaining)

        # 连接信号到槽函数（用于跨线程UI更新）
        self.remaining_signal.connect(self._update_remaining_loops)
        self.status_signal.connect(self._update_play_status_text)

        # 创建界面
        self._create_widgets()

        # 设置全局热键
        self._setup_hotkeys()

        # 刷新文件列表
        self._refresh_file_list()

    def _create_widgets(self) -> None:
        """创建界面组件"""
        # 主分割器（左右布局）
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # === 左侧控制面板 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # 录制区域
        record_group = QGroupBox("录制")
        record_layout = QVBoxLayout(record_group)

        # 录制按钮行
        btn_layout = QHBoxLayout()
        self.btn_start_record = QPushButton("开始录制 (F9)")
        self.btn_start_record.clicked.connect(self._start_recording)
        btn_layout.addWidget(self.btn_start_record)

        self.btn_stop_record = QPushButton("停止录制 (F9)")
        self.btn_stop_record.clicked.connect(self._stop_recording)
        self.btn_stop_record.setEnabled(False)
        btn_layout.addWidget(self.btn_stop_record)
        record_layout.addLayout(btn_layout)

        # 录制状态标签
        self.lbl_record_status = QLabel("状态: 就绪")
        record_layout.addWidget(self.lbl_record_status)

        left_layout.addWidget(record_group)

        # 回放区域
        playback_group = QGroupBox("回放")
        playback_layout = QVBoxLayout(playback_group)

        # 文件选择行
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("录制文件:"))
        self.lbl_selected_file = QLabel("未选择")
        self.lbl_selected_file.setStyleSheet("color: gray;")
        file_layout.addWidget(self.lbl_selected_file)
        btn_select = QPushButton("选择...")
        btn_select.clicked.connect(self._select_file)
        file_layout.addWidget(btn_select)
        playback_layout.addLayout(file_layout)

        # 循环设置行
        loop_layout = QHBoxLayout()
        loop_layout.addWidget(QLabel("循环次数:"))
        self.spin_loops = QSpinBox()
        self.spin_loops.setRange(1, 9999)
        self.spin_loops.setValue(1)
        loop_layout.addWidget(self.spin_loops)
        loop_layout.addSpacing(20)
        loop_layout.addWidget(QLabel("间隔(秒):"))
        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(0, 999)
        self.spin_interval.setSingleStep(0.5)
        self.spin_interval.setValue(0)
        loop_layout.addWidget(self.spin_interval)
        playback_layout.addLayout(loop_layout)

        # 回放按钮行
        play_btn_layout = QHBoxLayout()
        self.btn_play = QPushButton("开始回放")
        self.btn_play.clicked.connect(self._start_playback)
        play_btn_layout.addWidget(self.btn_play)

        self.btn_stop_play = QPushButton("停止回放 (ESC)")
        self.btn_stop_play.clicked.connect(self._stop_playback)
        self.btn_stop_play.setEnabled(False)
        play_btn_layout.addWidget(self.btn_stop_play)
        playback_layout.addLayout(play_btn_layout)

        # 回放状态标签
        self.lbl_play_status = QLabel("状态: 就绪")
        playback_layout.addWidget(self.lbl_play_status)

        left_layout.addWidget(playback_group)

        # 文件列表区域
        list_group = QGroupBox("录制文件列表")
        list_layout = QVBoxLayout(list_group)

        self.listbox = QListWidget()
        self.listbox.itemClicked.connect(self._on_file_select)
        self.listbox.itemDoubleClicked.connect(self._select_file_from_list)
        list_layout.addWidget(self.listbox)

        # 文件操作按钮行
        file_btn_layout = QHBoxLayout()
        btn_rename = QPushButton("重命名")
        btn_rename.clicked.connect(self._rename_selected)
        file_btn_layout.addWidget(btn_rename)

        btn_delete = QPushButton("删除")
        btn_delete.clicked.connect(self._delete_selected)
        file_btn_layout.addWidget(btn_delete)

        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self._refresh_file_list)
        file_btn_layout.addWidget(btn_refresh)

        btn_folder = QPushButton("打开文件夹")
        btn_folder.clicked.connect(self._open_folder)
        file_btn_layout.addWidget(btn_folder)
        list_layout.addLayout(file_btn_layout)

        left_layout.addWidget(list_group)

        splitter.addWidget(left_panel)

        # === 右侧浏览器区域 ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 浏览器标题栏
        browser_header = QWidget()
        browser_header.setFixedHeight(28)
        header_layout = QHBoxLayout(browser_header)
        header_layout.setContentsMargins(5, 2, 5, 2)
        header_layout.setSpacing(5)

        # URL输入框
        self.url_input = QLineEdit()
        self.url_input.setText(self.GAME_URL)
        self.url_input.setPlaceholderText("输入网址...")
        self.url_input.returnPressed.connect(self._refresh_browser)
        header_layout.addWidget(self.url_input)

        # 清空缓存按钮
        btn_clear_cache = QPushButton("清空缓存")
        btn_clear_cache.setFixedSize(70, 22)
        btn_clear_cache.clicked.connect(self._clear_browser_cache)
        header_layout.addWidget(btn_clear_cache)

        # 跳转按钮
        btn_refresh_browser = QPushButton("跳转")
        btn_refresh_browser.setFixedSize(50, 22)
        btn_refresh_browser.clicked.connect(self._refresh_browser)
        header_layout.addWidget(btn_refresh_browser)

        right_layout.addWidget(browser_header)

        # 浏览器 - 使用持久化profile保存cookie
        self.browser = QWebEngineView()

        # 创建持久化profile，cookie将保存在指定目录
        self.browser_data_dir = os.path.join(os.path.dirname(__file__), "browser_data")
        os.makedirs(self.browser_data_dir, exist_ok=True)

        self.browser_profile = QWebEngineProfile("GameBrowser", self.browser)
        self.browser_profile.setPersistentStoragePath(os.path.join(self.browser_data_dir, "storage"))
        self.browser_profile.setCachePath(os.path.join(self.browser_data_dir, "cache"))

        # 创建使用该profile的页面
        page = QWebEnginePage(self.browser_profile, self.browser)
        self.browser.setPage(page)
        self.browser.setUrl(QUrl(self.GAME_URL))

        # 监听URL变化，更新输入框
        self.browser.urlChanged.connect(self._on_url_changed)

        # 设置页面属性，隐藏滚动条
        settings = self.browser.page().settings()
        settings.setAttribute(QWebEngineSettings.ShowScrollBars, False)

        # 使用容器保持16:9比例
        self.browser_container = BrowserContainer(self.browser)
        right_layout.addWidget(self.browser_container)

        splitter.addWidget(right_panel)

        # 设置分割比例（左侧320像素，右侧880像素）
        splitter.setSizes([320, 880])

    def _setup_hotkeys(self) -> None:
        """设置全局热键 (F9控制录制)"""
        from pynput import keyboard

        def on_press(key):
            if key == keyboard.Key.f9:
                # 使用QTimer在主线程执行UI操作
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, self._toggle_recording)

        self._hotkey_listener = keyboard.Listener(on_press=on_press)
        self._hotkey_listener.start()

    def _toggle_recording(self) -> None:
        """切换录制状态 - F9热键调用，始终有效"""
        if self.recorder.is_recording:
            self._stop_recording()
        else:
            # 如果在回放中，先停止回放
            if self.player.is_playing:
                self._stop_playback()
            self._start_recording()

    def _refresh_browser(self) -> None:
        """跳转到输入框中的URL"""
        url = self.url_input.text().strip()
        if url:
            # 如果没有协议前缀，添加 https://
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                self.url_input.setText(url)
            self.browser.setUrl(QUrl(url))

    def _on_url_changed(self, url: QUrl) -> None:
        """浏览器URL变化时更新输入框"""
        self.url_input.setText(url.toString())

    def _clear_browser_cache(self) -> None:
        """清空浏览器cookie和缓存"""
        import shutil

        reply = QMessageBox.question(
            self, "确认", "确定要清空浏览器缓存吗？这将清除登录状态。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 清除profile的cookie和缓存
            self.browser_profile.clearAllVisitedLinks()
            self.browser_profile.cookieStore().deleteAllCookies()

            # 清除存储目录
            storage_path = os.path.join(self.browser_data_dir, "storage")
            cache_path = os.path.join(self.browser_data_dir, "cache")

            if os.path.exists(storage_path):
                shutil.rmtree(storage_path)
            if os.path.exists(cache_path):
                shutil.rmtree(cache_path)

            # 重新创建目录
            os.makedirs(storage_path, exist_ok=True)
            os.makedirs(cache_path, exist_ok=True)

            # 刷新页面
            self.browser.reload()

            QMessageBox.information(self, "完成", "缓存已清空")

    def _start_recording(self) -> None:
        """开始录制"""
        # 如果在回放中，先停止回放（互斥）
        if self.player.is_playing:
            self._stop_playback()

        name = datetime.now().strftime('%H时%M分%S秒')
        self.recorder.start(name)

        # 更新UI状态
        self.btn_start_record.setEnabled(False)
        self.btn_stop_record.setEnabled(True)
        self.btn_play.setEnabled(False)  # 禁用回放按钮
        self.lbl_record_status.setText("状态: 录制中 (已录制 0 个操作)")

        # 将焦点设置到浏览器
        self.browser.setFocus()
        self.browser.activateWindow()
        self.raise_()
        self.activateWindow()

    def _stop_recording(self) -> None:
        """停止录制并自动保存"""
        self._current_recording = self.recorder.stop()

        # 更新UI状态
        self.btn_start_record.setEnabled(True)
        self.btn_stop_record.setEnabled(False)
        self.btn_play.setEnabled(True)  # 恢复回放按钮

        # 自动保存录制
        if self._current_recording and self._current_recording.action_count > 0:
            # 使用 HH时MM分SS秒.json 格式
            filename = f"{datetime.now().strftime('%H时%M分%S秒')}.json"
            filepath = os.path.join(self.RECORDINGS_DIR, filename)

            # 如果文件已存在，添加序号
            counter = 1
            while os.path.exists(filepath):
                filename = f"{datetime.now().strftime('%H时%M分%S秒')}_{counter}.json"
                filepath = os.path.join(self.RECORDINGS_DIR, filename)
                counter += 1

            try:
                self._current_recording.to_json(filepath)
                self._refresh_file_list()
                self.lbl_record_status.setText(f"状态: 已保存 {filename} (共 {self._current_recording.action_count} 个操作)")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")
                self.lbl_record_status.setText(f"状态: 保存失败 (共 {self._current_recording.action_count} 个操作)")
        else:
            self.lbl_record_status.setText("状态: 已停止 (无操作记录)")

    def _on_action_recorded(self, count: int) -> None:
        """操作录制回调 - 使用QTimer确保在主线程更新UI"""
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._update_record_status)

    def _update_record_status(self) -> None:
        """更新录制状态显示"""
        count = self.recorder.action_count
        self.lbl_record_status.setText(f"状态: 录制中 (已录制 {count} 个操作)")

    def _select_file(self) -> None:
        """通过文件对话框选择录制文件"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "选择录制文件",
            self.RECORDINGS_DIR,
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        if filepath:
            self._selected_file = filepath
            self.lbl_selected_file.setText(os.path.basename(filepath))
            self.lbl_selected_file.setStyleSheet("color: black;")

    def _select_file_from_list(self) -> None:
        """从列表双击选择文件"""
        item = self.listbox.currentItem()
        if item:
            filename = item.text().split(" - ")[0]
            self._selected_file = os.path.join(self.RECORDINGS_DIR, filename)
            self.lbl_selected_file.setText(filename)
            self.lbl_selected_file.setStyleSheet("color: black;")

    def _on_file_select(self, item: QListWidgetItem) -> None:
        """文件列表单击选择事件"""
        filename = item.text().split(" - ")[0]
        self._selected_file = os.path.join(self.RECORDINGS_DIR, filename)
        self.lbl_selected_file.setText(filename)
        self.lbl_selected_file.setStyleSheet("color: black;")

    def _start_playback(self) -> None:
        """开始回放"""
        # 检查是否在录制中（互斥）
        if self.recorder.is_recording:
            QMessageBox.warning(self, "警告", "录制中无法开始回放")
            return

        # 检查是否选择了文件
        if not self._selected_file or not os.path.exists(self._selected_file):
            QMessageBox.warning(self, "警告", "请先选择录制文件")
            return

        # 加载录制文件
        try:
            recording = Recording.from_json(self._selected_file)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载录制文件失败: {e}")
            return

        if recording.action_count == 0:
            QMessageBox.warning(self, "警告", "录制文件为空")
            return

        # 获取回放参数
        loops = self.spin_loops.value()
        interval = self.spin_interval.value()

        # 更新UI状态
        self.btn_play.setEnabled(False)
        self.btn_stop_play.setEnabled(True)
        self.btn_start_record.setEnabled(False)  # 禁用录制按钮
        self.lbl_play_status.setText("状态: 回放中...")

        # 异步执行回放
        self.player.play_async(recording, loops=loops, interval=interval)

    def _stop_playback(self) -> None:
        """停止回放"""
        self.player.stop()
        # 更新UI状态
        self.btn_play.setEnabled(True)
        self.btn_stop_play.setEnabled(False)
        self.btn_start_record.setEnabled(True)  # 恢复录制按钮
        self.lbl_play_status.setText("状态: 已停止")

    def _on_play_status(self, status: str) -> None:
        """回放状态回调 - 通过信号更新UI"""
        self.status_signal.emit(status)

    def _update_play_status_text(self, status: str) -> None:
        """更新回放状态显示"""
        self.lbl_play_status.setText(f"状态: {status}")
        if status == "回放完成" or status == "已停止":
            self.btn_play.setEnabled(True)
            self.btn_stop_play.setEnabled(False)
            self.btn_start_record.setEnabled(True)  # 恢复录制按钮

    def _on_play_remaining(self, remaining: int) -> None:
        """回放剩余次数回调 - 通过信号更新UI"""
        self.remaining_signal.emit(remaining)

    def _update_remaining_loops(self, remaining: int) -> None:
        """更新剩余次数显示"""
        self.spin_loops.setValue(remaining)

    def _refresh_file_list(self) -> None:
        """刷新录制文件列表"""
        self.listbox.clear()

        if not os.path.exists(self.RECORDINGS_DIR):
            return

        # 按修改时间倒序排列
        for filename in sorted(os.listdir(self.RECORDINGS_DIR), reverse=True):
            if filename.endswith('.json'):
                filepath = os.path.join(self.RECORDINGS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    action_count = len(data.get('actions', []))
                    created_at = data.get('created_at', '')[:16].replace('T', ' ')
                    self.listbox.addItem(f"{filename} - {created_at} - {action_count}个操作")
                except Exception:
                    self.listbox.addItem(filename)

    def _rename_selected(self) -> None:
        """重命名选中的文件"""
        item = self.listbox.currentItem()
        if not item:
            QMessageBox.warning(self, "警告", "请先选择要重命名的文件")
            return

        old_filename = item.text().split(" - ")[0]
        old_filepath = os.path.join(self.RECORDINGS_DIR, old_filename)

        # 弹出输入框获取新文件名
        new_name, ok = QInputDialog.getText(
            self, "重命名", "请输入新文件名:",
            QLineEdit.Normal, old_filename.replace('.json', '')
        )

        if ok and new_name:
            new_name = new_name.strip()
            if not new_name.endswith('.json'):
                new_name += '.json'
            new_filepath = os.path.join(self.RECORDINGS_DIR, new_name)

            # 检查是否同名
            if old_filepath == new_filepath:
                return

            if os.path.exists(new_filepath):
                QMessageBox.warning(self, "警告", "文件名已存在")
                return

            try:
                os.rename(old_filepath, new_filepath)
                self._refresh_file_list()
                # 更新选中文件路径
                if self._selected_file == old_filepath:
                    self._selected_file = new_filepath
                    self.lbl_selected_file.setText(new_name)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名失败: {e}")

    def _delete_selected(self) -> None:
        """删除选中的文件"""
        item = self.listbox.currentItem()
        if not item:
            QMessageBox.warning(self, "警告", "请先选择要删除的文件")
            return

        filename = item.text().split(" - ")[0]
        filepath = os.path.join(self.RECORDINGS_DIR, filename)

        # 确认删除
        reply = QMessageBox.question(
            self, "确认", f"确定要删除 {filename} 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                os.remove(filepath)
                self._refresh_file_list()
                # 清除选中状态
                if self._selected_file == filepath:
                    self._selected_file = None
                    self.lbl_selected_file.setText("未选择")
                    self.lbl_selected_file.setStyleSheet("color: gray;")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def _open_folder(self) -> None:
        """打开录制文件夹"""
        import subprocess
        subprocess.run(['explorer', self.RECORDINGS_DIR])

    def closeEvent(self, event) -> None:
        """窗口关闭事件 - 清理资源"""
        if self.recorder.is_recording:
            self.recorder.stop()

        if self.player.is_playing:
            self.player.stop()

        if hasattr(self, '_hotkey_listener'):
            self._hotkey_listener.stop()

        event.accept()


def main():
    """主函数 - 创建并显示应用窗口"""
    import sys
    app = QApplication(sys.argv)
    window = RecorderApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
