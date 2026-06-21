from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QGroupBox, QFileDialog, QComboBox,
    QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.file_namer import NamingTemplate, PageRangeParser
from core.conversion_manager import ExportSettings


class ExportPanel(QWidget):
    settingsChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = ExportSettings()
        self._init_ui()
        self._connect_signals()
        self._emit_changed()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("导出设置")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        layout.addWidget(title)

        output_group = QGroupBox("输出目录")
        output_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e4e7ed;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #303133;
            }
        """)
        output_layout = QVBoxLayout(output_group)

        path_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("选择输出目录...")
        self.output_path_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #409eff;
            }
        """)
        path_layout.addWidget(self.output_path_edit, 1)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
        """)
        path_layout.addWidget(self.browse_btn)
        output_layout.addLayout(path_layout)

        self.subfolder_check = QCheckBox("按源文件名创建独立子文件夹")
        self.subfolder_check.setChecked(True)
        output_layout.addWidget(self.subfolder_check)

        layout.addWidget(output_group)

        naming_group = QGroupBox("文件命名")
        naming_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e4e7ed;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #303133;
            }
        """)
        naming_layout = QVBoxLayout(naming_group)

        template_label = QLabel("命名模板：")
        naming_layout.addWidget(template_label)

        self.template_edit = QLineEdit(NamingTemplate.DEFAULT_TEMPLATE)
        self.template_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                font-family: monospace;
            }
            QLineEdit:focus {
                border-color: #409eff;
            }
        """)
        naming_layout.addWidget(self.template_edit)

        placeholders_label = QLabel("可用占位符：")
        placeholders_label.setStyleSheet("color: #909399; font-size: 12px; margin-top: 8px;")
        naming_layout.addWidget(placeholders_label)

        placeholder_layout = QHBoxLayout()
        placeholder_layout.setSpacing(6)

        placeholders = [
            "[原文件名]", "[页码]", "[总页数]", "[DPI]", "[日期]", "[格式]"
        ]
        for ph in placeholders:
            btn = QPushButton(ph)
            btn.setStyleSheet("""
                QPushButton {
                    background: #ecf5ff;
                    color: #409eff;
                    border: 1px solid #d9ecff;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #d9ecff;
                }
            """)
            btn.clicked.connect(lambda checked, p=ph: self._insert_placeholder(p))
            placeholder_layout.addWidget(btn)

        placeholder_layout.addStretch()
        naming_layout.addLayout(placeholder_layout)

        layout.addWidget(naming_group)

        page_group = QGroupBox("页码范围")
        page_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e4e7ed;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #303133;
            }
        """)
        page_layout = QVBoxLayout(page_group)

        self.page_range_edit = QLineEdit()
        self.page_range_edit.setPlaceholderText("留空表示全部导出。示例：1-5, 8, 10-15")
        self.page_range_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #409eff;
            }
        """)
        page_layout.addWidget(self.page_range_edit)

        page_hint = QLabel("支持范围（如 1-5）和单页（如 8），用逗号分隔")
        page_hint.setStyleSheet("color: #909399; font-size: 12px;")
        page_layout.addWidget(page_hint)

        layout.addWidget(page_group)

        layout.addStretch()

    def _connect_signals(self):
        self.browse_btn.clicked.connect(self._on_browse)
        self.output_path_edit.textChanged.connect(self._emit_changed)
        self.subfolder_check.toggled.connect(self._emit_changed)
        self.template_edit.textChanged.connect(self._emit_changed)
        self.page_range_edit.textChanged.connect(self._on_page_range_changed)

    def _on_browse(self):
        directory = QFileDialog.getExistingDirectory(
            self, "选择输出目录", ""
        )
        if directory:
            self.output_path_edit.setText(directory)

    def _insert_placeholder(self, placeholder: str):
        cursor = self.template_edit.cursorPosition()
        text = self.template_edit.text()
        new_text = text[:cursor] + placeholder + text[cursor:]
        self.template_edit.setText(new_text)
        self.template_edit.setCursorPosition(cursor + len(placeholder))

    def _on_page_range_changed(self):
        text = self.page_range_edit.text()
        if text and not PageRangeParser.validate(text):
            self.page_range_edit.setStyleSheet("""
                QLineEdit {
                    padding: 6px;
                    border: 1px solid #f56c6c;
                    border-radius: 4px;
                    background: #fef0f0;
                }
            """)
        else:
            self.page_range_edit.setStyleSheet("""
                QLineEdit {
                    padding: 6px;
                    border: 1px solid #dcdfe6;
                    border-radius: 4px;
                }
                QLineEdit:focus {
                    border-color: #409eff;
                }
            """)
        self._emit_changed()

    def _emit_changed(self):
        self._settings.output_dir = self.output_path_edit.text()
        self._settings.naming_template = self.template_edit.text()
        self._settings.page_range = self.page_range_edit.text()
        self._settings.create_subfolder = self.subfolder_check.isChecked()
        self.settingsChanged.emit(self._settings)

    def get_settings(self) -> ExportSettings:
        return self._settings
