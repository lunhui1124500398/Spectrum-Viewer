"""
SpectrumViewer - 程序入口
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication, QToolTip
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from specview.ui.main_window import MainWindow


def main():
    """程序主入口"""
    # 启用高DPI缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # 设置应用属性
    app.setApplicationName("SpectrumViewer")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("HuanLab")
    
    # 设置默认字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # 强制设置ToolTip字体，防止QFont警告
    QToolTip.setFont(font)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
