from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt


class PasswordDialog(QDialog):
    def __init__(self, file_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF 密码")
        self.setFixedWidth(380)
        self.password = ""
        self._init_ui(file_name)

    def _init_ui(self, file_name: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = QLabel("此 PDF 文件已加密")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)

        file_label = QLabel(f"文件：{file_name}")
        file_label.setStyleSheet("color: #666;")
        file_label.setWordWrap(True)
        layout.addWidget(file_label)

        layout.addSpacing(5)

        password_label = QLabel("请输入密码：")
        layout.addWidget(password_label)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("输入 PDF 密码")
        self.password_edit.returnPressed.connect(self._on_ok)
        layout.addWidget(self.password_edit)

        self.show_password_btn = QPushButton("显示密码")
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.toggled.connect(self._toggle_password)
        self.show_password_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #666;
                text-align: left;
                padding: 0;
            }
            QPushButton:hover {
                color: #333;
            }
        """)
        layout.addWidget(self.show_password_btn)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(80)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        ok_btn.setDefault(True)
        ok_btn.setMinimumWidth(80)
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #409eff;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #66b1ff;
            }
            QPushButton:pressed {
                background: #3a8ee6;
            }
        """)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def _toggle_password(self, checked: bool):
        if checked:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_password_btn.setText("隐藏密码")
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password_btn.setText("显示密码")

    def _on_ok(self):
        password = self.password_edit.text()
        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            return
        self.password = password
        self.accept()

    def get_password(self) -> str:
        return self.password
