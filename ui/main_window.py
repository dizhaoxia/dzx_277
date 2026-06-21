import os
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QProgressBar, QLabel, QMessageBox, QTabWidget,
    QStatusBar, QListWidget, QListWidgetItem, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QColor

from ui.import_panel import ImportPanel
from ui.settings_panel import SettingsPanel
from ui.export_panel import ExportPanel
from ui.stitch_panel import StitchPanel
from ui.preview_panel import PreviewPanel
from ui.password_dialog import PasswordDialog

from core.conversion_manager import (
    ConversionManager, ConversionTask, PdfItem,
    ConversionSettings, ExportSettings, StitchSettings
)
from core.image_converter import format_file_size, OutputInfo
from core.pdf_parser import PdfMetadata


class ConversionWorker(QThread):
    progress = pyqtSignal(int)
    current_file = pyqtSignal(str)
    finished_all = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, tasks: list, parent=None):
        super().__init__(parent)
        self.tasks = tasks
        self.manager = ConversionManager()
        self._canceled = False

    def run(self):
        results = []
        total = len(self.tasks)

        for i, task in enumerate(self.tasks):
            if self._canceled:
                break

            self.current_file.emit(task.pdf_item.file_name)

            def on_progress(p, task_idx=i, total_tasks=total):
                overall = (task_idx + p / 100.0) / total_tasks * 100
                self.progress.emit(int(overall))

            result = self.manager.convert_single(task, on_progress)
            results.append(result)

        self.progress.emit(100)
        self.finished_all.emit(results)

    def cancel(self):
        self._canceled = True
        for task in self.tasks:
            task.cancel()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 转图片工具")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 800)

        self._conversion_settings = ConversionSettings()
        self._export_settings = ExportSettings()
        self._stitch_settings = StitchSettings()
        self._current_pdf: Optional[PdfItem] = None
        self._current_page = 1
        self._worker: Optional[ConversionWorker] = None
        self._pending_encrypted_files: list = []

        self._init_ui()
        self._connect_signals()
        self._set_default_output_dir()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background: #e4e7ed;
                width: 1px;
            }
        """)

        left_panel = self._create_left_panel()
        center_panel = self._create_center_panel()
        right_panel = self._create_right_panel()

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(center_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([320, 1, 360])

        main_layout.addWidget(main_splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.import_panel = ImportPanel()
        layout.addWidget(self.import_panel)

        return panel

    def _create_center_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.preview_panel = PreviewPanel()
        layout.addWidget(self.preview_panel, 1)

        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                text-align: center;
                background: #f5f7fa;
            }
            QProgressBar::chunk {
                background: #409eff;
                border-radius: 3px;
            }
        """)
        bottom_layout.addWidget(self.progress_bar, 1)

        self.start_btn = QPushButton("开始转换")
        self.start_btn.setMinimumWidth(120)
        self.start_btn.setMinimumHeight(36)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #67c23a;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #85ce61;
            }
            QPushButton:pressed {
                background: #5daf34;
            }
            QPushButton:disabled {
                background: #c0c4cc;
            }
        """)
        bottom_layout.addWidget(self.start_btn)

        layout.addWidget(bottom_bar)

        return panel

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e4e7ed;
                border-radius: 4px;
                top: -1px;
            }
            QTabBar::tab {
                background: #f5f7fa;
                border: 1px solid #e4e7ed;
                border-bottom: none;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                color: #606266;
            }
            QTabBar::tab:selected {
                background: white;
                color: #409eff;
                border-color: #409eff;
            }
            QTabBar::tab:hover:!selected {
                color: #409eff;
            }
        """)

        self.settings_panel = SettingsPanel()
        self.export_panel = ExportPanel()
        self.stitch_panel = StitchPanel()

        scroll_settings = self._wrap_in_scroll(self.settings_panel)
        scroll_export = self._wrap_in_scroll(self.export_panel)
        scroll_stitch = self._wrap_in_scroll(self.stitch_panel)

        self.tab_widget.addTab(scroll_settings, "参数设置")
        self.tab_widget.addTab(scroll_export, "导出设置")
        self.tab_widget.addTab(scroll_stitch, "长图拼接")

        layout.addWidget(self.tab_widget)

        return panel

    def _wrap_in_scroll(self, widget: QWidget) -> QWidget:
        from PyQt6.QtWidgets import QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(widget)
        return scroll

    def _connect_signals(self):
        self.import_panel.currentPdfChanged.connect(self._on_current_pdf_changed)
        self.import_panel.pdfItemsChanged.connect(self._on_pdf_items_changed)

        self.settings_panel.settingsChanged.connect(self._on_settings_changed)
        self.export_panel.settingsChanged.connect(self._on_export_settings_changed)
        self.stitch_panel.settingsChanged.connect(self._on_stitch_settings_changed)

        self.preview_panel.pageChanged.connect(self._on_page_changed)

        self.start_btn.clicked.connect(self._on_start_clicked)

    def _set_default_output_dir(self):
        home = os.path.expanduser("~")
        default_dir = os.path.join(home, "Desktop", "PDF输出")
        self.export_panel.output_path_edit.setText(default_dir)

    def _on_current_pdf_changed(self, pdf_item: PdfItem):
        self._current_pdf = pdf_item
        self._current_page = 1

        if pdf_item and pdf_item.metadata and pdf_item.is_loaded:
            self.settings_panel.set_current_metadata(pdf_item.metadata)
            total_pages = pdf_item.metadata.total_pages
            self.preview_panel.set_page_info(1, total_pages)
            self._update_preview()
        else:
            self.settings_panel.set_current_metadata(None)
            self.preview_panel.set_images(None, None)
            self.preview_panel.set_page_info(0, 0)

    def _on_pdf_items_changed(self):
        items = self.import_panel.get_pdf_items()
        loaded_count = sum(1 for item in items if item.is_loaded)
        self.status_bar.showMessage(
            f"共 {len(items)} 个文件，{loaded_count} 个已就绪"
        )
        self.start_btn.setEnabled(loaded_count > 0)

        encrypted_items = [item for item in items 
                          if not item.is_loaded and not item.is_error 
                          and item.file_path not in self._pending_encrypted_files]
        
        if encrypted_items:
            self._process_next_encrypted(encrypted_items)

    def _process_next_encrypted(self, items: list):
        if not items:
            return

        item = items.pop(0)
        self._pending_encrypted_files.append(item.file_path)
        self._ask_password_for_pdf(item, items)

    def _ask_password_for_pdf(self, pdf_item: PdfItem, remaining_items: list):
        dialog = PasswordDialog(pdf_item.file_name, self)
        result = dialog.exec()

        if result == dialog.DialogCode.Accepted:
            password = dialog.get_password()
            success = self.import_panel.set_pdf_password(
                pdf_item.file_path, password
            )
            
            if not success:
                QMessageBox.warning(self, "密码错误", 
                                   "密码不正确，请重新输入。")
                self._ask_password_for_pdf(pdf_item, remaining_items)
                return

        if remaining_items:
            self._process_next_encrypted(remaining_items)

    def _on_settings_changed(self, settings: ConversionSettings):
        self._conversion_settings = settings
        if self._current_pdf and self._current_pdf.is_loaded:
            self._update_preview()

    def _on_export_settings_changed(self, settings: ExportSettings):
        self._export_settings = settings

    def _on_stitch_settings_changed(self, settings: StitchSettings):
        self._stitch_settings = settings

    def _on_page_changed(self, page: int):
        self._current_page = page
        self._update_preview()

    def _update_preview(self):
        if not self._current_pdf or not self._current_pdf.is_loaded:
            return

        manager = ConversionManager()

        preview_dpi = min(self._conversion_settings.dpi, 300)

        original_img = manager.preview_page(
            self._current_pdf, self._current_page - 1, dpi=preview_dpi
        )

        output_img = manager.preview_converted(
            self._current_pdf, self._current_page - 1,
            self._conversion_settings
        )

        output_info = None
        if output_img:
            from core.image_converter import ImageConverter
            min_size, max_size = ImageConverter.estimate_file_size(
                output_img.width, output_img.height, self._conversion_settings
            )
            output_info = OutputInfo(
                width=output_img.width,
                height=output_img.height,
                dpi=self._conversion_settings.dpi,
                format=self._conversion_settings.output_format.value.upper(),
                file_size=(min_size + max_size) // 2,
                color_mode=output_img.mode
            )

        self.preview_panel.set_images(original_img, output_img, output_info)

    def _on_start_clicked(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.start_btn.setText("取消中...")
            self.start_btn.setEnabled(False)
            return

        pdf_items = [item for item in self.import_panel.get_pdf_items() 
                     if item.is_loaded]

        if not pdf_items:
            QMessageBox.warning(self, "提示", "没有可转换的文件")
            return

        if not self._export_settings.output_dir:
            QMessageBox.warning(self, "提示", "请选择输出目录")
            self.tab_widget.setCurrentIndex(1)
            return

        if self._stitch_settings.enabled:
            all_warnings = []
            manager = ConversionManager()
            for item in pdf_items:
                export_settings = ExportSettings(
                    output_dir=self._export_settings.output_dir,
                    naming_template=self._export_settings.naming_template,
                    page_range=self._export_settings.page_range,
                    create_subfolder=self._export_settings.create_subfolder,
                    stitch_settings=self._stitch_settings
                )
                size_info = manager.estimate_stitch_size(
                    item, self._conversion_settings, export_settings
                )
                if size_info and size_info["warnings"]:
                    for warning in size_info["warnings"]:
                        all_warnings.append(f"• {item.file_name}: {warning}")

            if all_warnings:
                msg = "以下文件可能存在转换问题：\n\n" + "\n".join(all_warnings)
                msg += "\n\n建议降低 DPI 或减少拼接页数，或使用 PNG 格式。\n\n是否继续转换？"
                reply = QMessageBox.warning(
                    self, "尺寸警告", msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        tasks = []
        for item in pdf_items:
            export_settings = ExportSettings(
                output_dir=self._export_settings.output_dir,
                naming_template=self._export_settings.naming_template,
                page_range=self._export_settings.page_range,
                create_subfolder=self._export_settings.create_subfolder,
                stitch_settings=self._stitch_settings
            )
            task = ConversionTask(item, self._conversion_settings, export_settings)
            tasks.append(task)

        self._worker = ConversionWorker(tasks)
        self._worker.progress.connect(self._on_progress)
        self._worker.current_file.connect(self._on_current_file)
        self._worker.finished_all.connect(self._on_finished_all)
        self._worker.start()

        self.start_btn.setText("取消转换")
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("开始转换...")

    def _on_progress(self, value: int):
        self.progress_bar.setValue(value)

    def _on_current_file(self, file_name: str):
        self.status_bar.showMessage(f"正在处理：{file_name}")

    def _on_finished_all(self, results: list):
        self._worker = None
        self.start_btn.setText("开始转换")
        self.start_btn.setEnabled(True)

        success_count = sum(1 for r in results if r.success)
        total_size = sum(r.total_size for r in results)

        message = (f"转换完成！\n"
                   f"成功：{success_count}/{len(results)} 个文件\n"
                   f"总大小：{format_file_size(total_size)}")

        failed = [r for r in results if not r.success]
        if failed:
            message += f"\n\n失败：{len(failed)} 个"
            for r in failed[:5]:
                message += f"\n  - {r.pdf_item.file_name}: {r.error_message}"

        QMessageBox.information(self, "转换完成", message)
        self.status_bar.showMessage(
            f"转换完成，成功 {success_count}/{len(results)} 个"
        )
