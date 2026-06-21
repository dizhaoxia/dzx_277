from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QListWidget, QListWidgetItem, QCheckBox,
    QSlider, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.image_processor import FilterChain, FilterConfig, FilterType


class FilterItemWidget(QFrame):
    enabledChanged = pyqtSignal(int, bool)
    intensityChanged = pyqtSignal(int, float)

    def __init__(self, index: int, filter_cfg: FilterConfig, parent=None):
        super().__init__(parent)
        self.index = index
        self.filter_cfg = filter_cfg
        self._init_ui()
        self._connect_signals()
        self._update_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e4e7ed;
                border-radius: 6px;
            }
            QFrame:hover {
                border-color: #c6e2ff;
                background: #f5faff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        self.enable_check = QCheckBox()
        self.enable_check.setChecked(self.filter_cfg.enabled)
        header_layout.addWidget(self.enable_check)

        self.name_label = QLabel(self._get_filter_name())
        self.name_label.setStyleSheet("font-weight: bold; color: #303133;")
        header_layout.addWidget(self.name_label)

        handle_label = QLabel("⋮⋮")
        handle_label.setStyleSheet("color: #c0c4cc; font-size: 14px;")
        handle_label.setCursor(Qt.CursorShape.SizeAllCursor)
        header_layout.addStretch()
        header_layout.addWidget(handle_label)

        layout.addLayout(header_layout)

        self.intensity_container = QWidget()
        intensity_layout = QHBoxLayout(self.intensity_container)
        intensity_layout.setContentsMargins(24, 0, 0, 0)
        intensity_layout.setSpacing(8)

        intensity_layout.addWidget(QLabel("强度:"))

        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(1, 100)
        self.intensity_slider.setValue(int(self.filter_cfg.intensity * 50))
        intensity_layout.addWidget(self.intensity_slider, 1)

        self.intensity_value = QLabel(f"{self.filter_cfg.intensity:.1f}")
        self.intensity_value.setMinimumWidth(35)
        self.intensity_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.intensity_value.setStyleSheet("color: #409eff; font-weight: bold;")
        intensity_layout.addWidget(self.intensity_value)

        layout.addWidget(self.intensity_container)

        desc_label = QLabel(self._get_filter_desc())
        desc_label.setStyleSheet("color: #909399; font-size: 11px; padding-left: 24px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

    def _get_filter_name(self) -> str:
        names = {
            FilterType.SHARPEN: "锐化增强",
            FilterType.CONTRAST_STRETCH: "对比度自动拉伸",
            FilterType.DENOISE: "轻度去噪",
        }
        return names.get(self.filter_cfg.filter_type, "未知滤镜")

    def _get_filter_desc(self) -> str:
        descs = {
            FilterType.SHARPEN: "增强图像边缘和细节，使文字更清晰",
            FilterType.CONTRAST_STRETCH: "自动扩展灰度范围，适合发灰的扫描件",
            FilterType.DENOISE: "减少扫描噪点和颗粒感，平滑图像",
        }
        return descs.get(self.filter_cfg.filter_type, "")

    def _connect_signals(self):
        self.enable_check.toggled.connect(self._on_enabled_changed)
        self.intensity_slider.valueChanged.connect(self._on_intensity_changed)

    def _on_enabled_changed(self, checked: bool):
        self.filter_cfg.enabled = checked
        self._update_ui()
        self.enabledChanged.emit(self.index, checked)

    def _on_intensity_changed(self, value: int):
        intensity = value / 50.0
        self.filter_cfg.intensity = intensity
        self.intensity_value.setText(f"{intensity:.1f}")
        self.intensityChanged.emit(self.index, intensity)

    def _update_ui(self):
        enabled = self.filter_cfg.enabled
        self.intensity_container.setEnabled(enabled)
        if self.filter_cfg.filter_type == FilterType.CONTRAST_STRETCH:
            self.intensity_container.setVisible(False)
        else:
            self.intensity_container.setVisible(True)

    def update_index(self, index: int):
        self.index = index


class FilterChainPanel(QWidget):
    settingsChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_chain = FilterChain()
        self._init_ui()
        self._connect_signals()
        self._refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("图像增强滤镜")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        layout.addWidget(title)

        hint = QLabel("提示：拖拽调整滤镜执行顺序，启用后实时预览效果")
        hint.setStyleSheet("color: #909399; font-size: 12px;")
        layout.addWidget(hint)

        filter_group = QGroupBox("滤镜链（可拖拽排序）")
        filter_group.setStyleSheet("""
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
        group_layout = QVBoxLayout(filter_group)
        group_layout.setContentsMargins(8, 8, 8, 8)

        self.filter_list = QListWidget()
        self.filter_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.filter_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.filter_list.setAlternatingRowColors(False)
        self.filter_list.setSpacing(4)
        self.filter_list.setStyleSheet("""
            QListWidget {
                background: #f5f7fa;
                border: 1px solid #e4e7ed;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                background: transparent;
                padding: 0;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background: transparent;
            }
        """)
        group_layout.addWidget(self.filter_list)

        btn_layout = QHBoxLayout()

        self.reset_btn = QPushButton("重置默认")
        self.reset_btn.setStyleSheet("""
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
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.move_up_btn = QPushButton("上移")
        self.move_up_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 6px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
        """)
        btn_layout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("下移")
        self.move_down_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 6px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
        """)
        btn_layout.addWidget(self.move_down_btn)

        group_layout.addLayout(btn_layout)
        layout.addWidget(filter_group)

        layout.addStretch()

    def _connect_signals(self):
        self.filter_list.model().rowsMoved.connect(self._on_rows_moved)
        self.reset_btn.clicked.connect(self._on_reset)
        self.move_up_btn.clicked.connect(self._on_move_up)
        self.move_down_btn.clicked.connect(self._on_move_down)

    def _refresh_list(self):
        self.filter_list.clear()
        for i, filter_cfg in enumerate(self._filter_chain.filters):
            item = QListWidgetItem()
            widget = FilterItemWidget(i, filter_cfg)
            widget.enabledChanged.connect(self._on_filter_changed)
            widget.intensityChanged.connect(self._on_filter_changed)
            item.setSizeHint(widget.sizeHint())
            self.filter_list.addItem(item)
            self.filter_list.setItemWidget(item, widget)

    def _on_rows_moved(self, parent, start, end, destination, row):
        self._sync_from_list()
        self._emit_changed()

    def _sync_from_list(self):
        filters = []
        for i in range(self.filter_list.count()):
            item = self.filter_list.item(i)
            widget = self.filter_list.itemWidget(item)
            if widget:
                widget.update_index(i)
                filters.append(widget.filter_cfg)
        self._filter_chain.filters = filters

    def _on_filter_changed(self, *args):
        self._sync_from_list()
        self._emit_changed()

    def _on_reset(self):
        self._filter_chain = FilterChain()
        self._refresh_list()
        self._emit_changed()

    def _on_move_up(self):
        current_row = self.filter_list.currentRow()
        if current_row > 0:
            self._filter_chain.move_filter(current_row, current_row - 1)
            self._refresh_list()
            self.filter_list.setCurrentRow(current_row - 1)
            self._emit_changed()

    def _on_move_down(self):
        current_row = self.filter_list.currentRow()
        if current_row < self.filter_list.count() - 1:
            self._filter_chain.move_filter(current_row, current_row + 1)
            self._refresh_list()
            self.filter_list.setCurrentRow(current_row + 1)
            self._emit_changed()

    def _emit_changed(self):
        self.settingsChanged.emit(self._filter_chain)

    def get_settings(self) -> FilterChain:
        return self._filter_chain

    def set_settings(self, filter_chain: FilterChain):
        self._filter_chain = FilterChain(filters=list(filter_chain.filters))
        self._refresh_list()
