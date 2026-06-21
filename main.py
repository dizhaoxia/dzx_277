#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PDF 转图片工具")
    app.setApplicationVersion("1.0.0")

    font = QFont("PingFang SC", 10)
    app.setFont(font)

    app.setStyleSheet("""
        QWidget {
            background: #fafafa;
            color: #303133;
        }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
