"""
网页操作录制与回放工具

主程序入口

功能概述：
1. 在内嵌浏览器中打开指定网页
2. 录制用户的键盘和鼠标操作（F9热键控制）
3. 将操作保存为JSON格式的录制文件
4. 支持循环回放录制的操作（可配置循环次数和间隔时间）
5. 提供友好的图形界面

使用方法：
1. 运行程序后，在浏览器中登录游戏
2. 按F9开始录制，进行游戏操作
3. 再按F9停止录制，自动保存
4. 选择录制文件，设置循环次数，开始回放
5. 按ESC可停止回放
"""
import os
import sys

# 抑制 Chromium/QtWebEngine 的控制台输出
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.webengine.debug=false'
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-logging --log-level=3 --silent-debugger-extension-api'

# 重定向 stderr 到 null，抑制 Chromium 底层警告
if sys.platform == 'win32':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    # 获取 null 设备句柄
    null_handle = kernel32.CreateFileW(
        'NUL',
        0x40000000,  # GENERIC_WRITE
        0x00000003,  # FILE_SHARE_READ | FILE_SHARE_WRITE
        None,
        0x03,        # OPEN_EXISTING
        0,
        None
    )
    # 重定向 stderr
    kernel32.SetStdHandle(0xFFFFFFF4, null_handle)  # STD_ERROR_HANDLE = -12


def main():
    """
    主函数

    创建并启动GUI应用程序。
    """
    from gui import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
