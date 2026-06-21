import os
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QFileDialog, QMessageBox, QMenu,
    QAbstractItemView, QLineEdit, QFrame
)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap, QColor

from core.pdf_parser import PdfParser, PdfMetadata
from core.conversion_manager import PdfItem


class DropZone(QLabel):
    filesDropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(100)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background: #fafafa;
                color: #999;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #409eff;
                background: #f0f9ff;
                color: #409eff;
            }
        """)
        self.setText("拖拽 PDF 文件到此处\n\n或点击下方按钮添加")
        self._drag_active = False

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drag_active = True
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #409eff;
                    border-radius: 8px;
                    background: #ecf5ff;
                    color: #409eff;
                    font-size: 14px;
                }
            """)
        else:
            super().dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        self._drag_active = False
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background: #fafafa;
                color: #999;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #409eff;
                background: #f0f9ff;
                color: #409eff;
            }
        """)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self._drag_active = False
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background: #fafafa;
                color: #999;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #409eff;
                background: #f0f9ff;
                color: #409eff;
            }
        """)

        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if os.path.isfile(path) and path.lower().endswith('.pdf'):
                        file_paths.append(path)
                    elif os.path.isdir(path):
                        for root, dirs, files in os.walk(path):
                            for f in files:
                                if f.lower().endswith('.pdf'):
                                    file_paths.append(os.path.join(root, f))
            if file_paths:
                self.filesDropped.emit(file_paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class PdfListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid #e4e7ed;
                border-radius: 4px;
                background: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background: #ecf5ff;
                color: #333;
            }
        """)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        remove_action = menu.addAction("移除选中")
        clear_action = menu.addAction("清空列表")

        action = menu.exec(event.globalPos())
        if action == remove_action:
            self._remove_selected()
        elif action == clear_action:
            self.clear()

    def _remove_selected(self):
        for item in self.selectedItems():
            self.takeItem(self.row(item))


class ImportPanel(QWidget):
    pdfItemsChanged = pyqtSignal()
    currentPdfChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf_items: List[PdfItem] = []
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("文件导入")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        layout.addWidget(title)

        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加文件")
        self.add_btn.setMinimumWidth(100)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: #409eff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #66b1ff;
            }
            QPushButton:pressed {
                background: #3a8ee6;
            }
        """)
        btn_layout.addWidget(self.add_btn)

        self.paste_btn = QPushButton("粘贴路径")
        self.paste_btn.setMinimumWidth(100)
        self.paste_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
        """)
        btn_layout.addWidget(self.paste_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("或直接在此输入 PDF 文件路径，多个路径用分号分隔")
        self.path_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #409eff;
            }
        """)
        layout.addWidget(self.path_input)

        list_title_layout = QHBoxLayout()
        list_label = QLabel("待处理列表")
        list_label.setStyleSheet("font-weight: bold; color: #303133;")
        list_title_layout.addWidget(list_label)

        self.count_label = QLabel("(0 个文件)")
        self.count_label.setStyleSheet("color: #909399;")
        list_title_layout.addWidget(self.count_label)
        list_title_layout.addStretch()
        layout.addLayout(list_title_layout)

        self.pdf_list = PdfListWidget()
        layout.addWidget(self.pdf_list, 1)

        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_frame.setStyleSheet("""
            QFrame {
                background: #f5f7fa;
                border: 1px solid #ebeef5;
                border-radius: 4px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(4)

        self.info_title = QLabel("文件信息")
        self.info_title.setStyleSheet("font-weight: bold; color: #303133;")
        info_layout.addWidget(self.info_title)

        self.info_content = QLabel("请选择一个 PDF 文件查看详情")
        self.info_content.setStyleSheet("color: #606266; font-size: 12px;")
        self.info_content.setWordWrap(True)
        info_layout.addWidget(self.info_content)

        layout.addWidget(info_frame)

    def _connect_signals(self):
        self.drop_zone.filesDropped.connect(self._on_files_dropped)
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.paste_btn.clicked.connect(self._on_paste_clicked)
        self.path_input.returnPressed.connect(self._on_path_input_return)
        self.pdf_list.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_files_dropped(self, file_paths: list):
        self._add_files(file_paths)

    def _on_add_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择 PDF 文件", "", "PDF 文件 (*.pdf)"
        )
        if files:
            self._add_files(files)

    def _on_paste_clicked(self):
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            paths = self._parse_paths(text)
            if paths:
                self._add_files(paths)
            else:
                QMessageBox.information(self, "提示", "剪贴板中没有有效的文件路径")
        else:
            QMessageBox.information(self, "提示", "剪贴板中没有有效的文件路径")

    def _on_path_input_return(self):
        text = self.path_input.text()
        if text:
            paths = self._parse_paths(text)
            if paths:
                self._add_files(paths)
                self.path_input.clear()

    def _parse_paths(self, text: str) -> list:
        paths = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            for p in line.split(';'):
                p = p.strip().strip('"').strip("'")
                if p and os.path.isfile(p) and p.lower().endswith('.pdf'):
                    paths.append(p)
        return paths

    def _add_files(self, file_paths: list):
        added_count = 0
        for path in file_paths:
            if self._is_duplicate(path):
                continue

            pdf_item = PdfItem(file_path=path)
            self._parse_pdf(pdf_item)
            self._pdf_items.append(pdf_item)
            self._add_list_item(pdf_item)
            added_count += 1

        if added_count > 0:
            self._update_count()
            self.pdfItemsChanged.emit()

    def _is_duplicate(self, file_path: str) -> bool:
        for item in self._pdf_items:
            if os.path.abspath(item.file_path) == os.path.abspath(file_path):
                return True
        return False

    def _parse_pdf(self, pdf_item: PdfItem):
        try:
            parser = PdfParser(pdf_item.file_path)
            if parser.open():
                pdf_item.metadata = parser.metadata
                pdf_item.is_loaded = True
                pdf_item.is_error = False
            else:
                if parser.is_encrypted:
                    pdf_item.is_loaded = False
                    pdf_item.is_error = False
                else:
                    pdf_item.is_error = True
                    pdf_item.error_message = "无法打开文件"
            parser.close()
        except Exception as e:
            pdf_item.is_error = True
            pdf_item.error_message = str(e)

    def _add_list_item(self, pdf_item: PdfItem):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, pdf_item)

        display_text = pdf_item.file_name

        if pdf_item.is_error:
            display_text += "  ⚠️ 错误"
            item.setForeground(QColor("#f56c6c"))
        elif not pdf_item.is_loaded:
            display_text += "  🔒 已加密"
            item.setForeground(QColor("#e6a23c"))
        else:
            if pdf_item.metadata:
                display_text += f"  ({pdf_item.metadata.total_pages} 页)"

        item.setText(display_text)
        self.pdf_list.addItem(item)

    def _update_count(self):
        self.count_label.setText(f"({len(self._pdf_items)} 个文件)")

    def _on_selection_changed(self):
        current_item = self.pdf_list.currentItem()
        if current_item:
            pdf_item = current_item.data(Qt.ItemDataRole.UserRole)
            self._update_info_panel(pdf_item)
            self.currentPdfChanged.emit(pdf_item)
        else:
            self.info_content.setText("请选择一个 PDF 文件查看详情")

    def _update_info_panel(self, pdf_item: PdfItem):
        if pdf_item.is_error:
            self.info_content.setText(
                f"<b>状态：</b>错误<br>"
                f"<b>错误信息：</b>{pdf_item.error_message}"
            )
            return

        if not pdf_item.is_loaded:
            self.info_content.setText(
                f"<b>状态：</b>已加密<br>"
                f"<b>文件：</b>{pdf_item.file_name}<br>"
                f"<b>请输入密码解锁</b>"
            )
            return

        if not pdf_item.metadata:
            self.info_content.setText("无可用信息")
            return

        meta = pdf_item.metadata
        size_mm = meta.page_size_mm

        info_text = (
            f"<b>文件名：</b>{meta.file_name}<br>"
            f"<b>总页数：</b>{meta.total_pages} 页<br>"
            f"<b>页面尺寸：</b>{size_mm[0]:.1f} × {size_mm[1]:.1f} mm<br>"
            f"<b>PDF 版本：</b>{meta.pdf_version if meta.pdf_version else '未知'}<br>"
            f"<b>加密状态：</b>{'已加密' if meta.is_encrypted else '未加密'}"
        )
        self.info_content.setText(info_text)

    def get_pdf_items(self) -> list:
        return self._pdf_items

    def get_selected_pdf_item(self):
        current_item = self.pdf_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None

    def set_pdf_password(self, file_path: str, password: str) -> bool:
        for i, pdf_item in enumerate(self._pdf_items):
            if pdf_item.file_path == file_path:
                pdf_item.password = password
                try:
                    parser = PdfParser(file_path)
                    if parser.open(password):
                        pdf_item.metadata = parser.metadata
                        pdf_item.is_loaded = True
                        pdf_item.is_error = False
                        parser.close()
                        self._refresh_list_item(i, pdf_item)
                        self._update_count()
                        self.pdfItemsChanged.emit()
                        return True
                    else:
                        pdf_item.is_error = True
                        pdf_item.error_message = "密码错误"
                        parser.close()
                        self._refresh_list_item(i, pdf_item)
                        return False
                except Exception as e:
                    pdf_item.is_error = True
                    pdf_item.error_message = str(e)
                    self._refresh_list_item(i, pdf_item)
                    return False
        return False

    def _refresh_list_item(self, index: int, pdf_item: PdfItem):
        if 0 <= index < self.pdf_list.count():
            item = self.pdf_list.item(index)
            display_text = pdf_item.file_name

            if pdf_item.is_error:
                display_text += "  ⚠️ 错误"
                item.setForeground(QColor("#f56c6c"))
            elif not pdf_item.is_loaded:
                display_text += "  🔒 已加密"
                item.setForeground(QColor("#e6a23c"))
            else:
                if pdf_item.metadata:
                    display_text += f"  ({pdf_item.metadata.total_pages} 页)"
                item.setForeground(QColor("#303133"))

            item.setText(display_text)
            item.setData(Qt.ItemDataRole.UserRole, pdf_item)
