from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QRadioButton, QButtonGroup, QSpinBox, QGroupBox,
    QComboBox, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from core.image_stitcher import (
    StitchDirection, BackgroundColor, WidthStrategy, HeightStrategy
)
from core.conversion_manager import StitchSettings, OutputMode


class StitchPanel(QWidget):
    settingsChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = StitchSettings()
        self._init_ui()
        self._connect_signals()
        self._update_enabled()
        self._update_mode_ui()
        self._emit_changed()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("长图拼接")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        layout.addWidget(title)

        self.enable_check = QCheckBox("启用长图拼接模式")
        self.enable_check.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                spacing: 8px;
            }
        """)
        layout.addWidget(self.enable_check)

        self.content_frame = QFrame()
        self.content_frame.setFrameShape(QFrame.Shape.NoFrame)
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 8, 0, 0)
        content_layout.setSpacing(10)

        mode_group = QGroupBox("输出模式")
        mode_group.setStyleSheet("""
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
        mode_layout = QVBoxLayout(mode_group)

        self.single_long_radio = QRadioButton("每个 PDF 单独生成长图")
        self.single_long_radio.setChecked(True)
        mode_layout.addWidget(self.single_long_radio)

        self.cross_long_radio = QRadioButton("跨文件合成长图（按文件顺序拼接）")
        mode_layout.addWidget(self.cross_long_radio)

        self.grid_radio = QRadioButton("缩略图网格（单 PDF 多页网格排列）")
        mode_layout.addWidget(self.grid_radio)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.single_long_radio, 0)
        self.mode_group.addButton(self.cross_long_radio, 1)
        self.mode_group.addButton(self.grid_radio, 2)

        content_layout.addWidget(mode_group)

        self.mode_stack = QStackedWidget()

        self.long_page = QWidget()
        long_layout = QVBoxLayout(self.long_page)
        long_layout.setContentsMargins(0, 0, 0, 0)
        long_layout.setSpacing(10)

        direction_group = QGroupBox("拼接方向")
        direction_group.setStyleSheet("""
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
        dir_layout = QHBoxLayout(direction_group)

        self.vertical_radio = QRadioButton("纵向（垂直长图）")
        self.vertical_radio.setChecked(True)
        dir_layout.addWidget(self.vertical_radio)

        self.horizontal_radio = QRadioButton("横向（水平长图）")
        dir_layout.addWidget(self.horizontal_radio)

        dir_layout.addStretch()
        long_layout.addWidget(direction_group)

        gap_group = QGroupBox("页间距")
        gap_group.setStyleSheet("""
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
        gap_layout = QHBoxLayout(gap_group)

        gap_layout.addWidget(QLabel("间隔像素："))
        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(0, 500)
        self.gap_spin.setValue(0)
        self.gap_spin.setSuffix(" px")
        self.gap_spin.setMinimumWidth(100)
        gap_layout.addWidget(self.gap_spin)
        gap_layout.addStretch()
        long_layout.addWidget(gap_group)

        bg_group = QGroupBox("背景色")
        bg_group.setStyleSheet("""
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
        bg_layout = QHBoxLayout(bg_group)

        self.bg_combo = QComboBox()
        self.bg_combo.addItem("白色", BackgroundColor.WHITE)
        self.bg_combo.addItem("黑色", BackgroundColor.BLACK)
        self.bg_combo.addItem("透明", BackgroundColor.TRANSPARENT)
        self.bg_combo.setMinimumWidth(120)
        bg_layout.addWidget(self.bg_combo)

        self.color_preview = QLabel("    ")
        self.color_preview.setFixedSize(30, 20)
        self.color_preview.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                background: white;
            }
        """)
        bg_layout.addWidget(self.color_preview)

        bg_layout.addStretch()
        long_layout.addWidget(bg_group)

        align_group = QGroupBox("宽度不一致时")
        align_group.setStyleSheet("""
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
        align_layout = QVBoxLayout(align_group)

        self.center_radio = QRadioButton("居中放置，填充背景色（推荐）")
        self.center_radio.setChecked(True)
        align_layout.addWidget(self.center_radio)

        self.stretch_radio = QRadioButton("统一拉伸至最大宽度（可能变形）")
        align_layout.addWidget(self.stretch_radio)

        long_layout.addWidget(align_group)
        long_layout.addStretch()

        self.grid_page = QWidget()
        grid_layout = QVBoxLayout(self.grid_page)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(10)

        cols_group = QGroupBox("网格设置")
        cols_group.setStyleSheet("""
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
        cols_form = QVBoxLayout(cols_group)

        col_row = QHBoxLayout()
        col_row.addWidget(QLabel("列数："))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 20)
        self.cols_spin.setValue(3)
        self.cols_spin.setSuffix(" 列")
        self.cols_spin.setMinimumWidth(100)
        col_row.addWidget(self.cols_spin)
        col_row.addStretch()
        cols_form.addLayout(col_row)

        cell_row = QHBoxLayout()
        cell_row.addWidget(QLabel("单格宽度："))
        self.cell_width_spin = QSpinBox()
        self.cell_width_spin.setRange(0, 4000)
        self.cell_width_spin.setValue(400)
        self.cell_width_spin.setSuffix(" px")
        self.cell_width_spin.setSpecialValueText("原始尺寸")
        self.cell_width_spin.setMinimumWidth(120)
        cell_row.addWidget(self.cell_width_spin)
        cell_row.addStretch()
        cols_form.addLayout(cell_row)

        grid_gap_row = QHBoxLayout()
        grid_gap_row.addWidget(QLabel("间隔像素："))
        self.grid_gap_spin = QSpinBox()
        self.grid_gap_spin.setRange(0, 500)
        self.grid_gap_spin.setValue(10)
        self.grid_gap_spin.setSuffix(" px")
        self.grid_gap_spin.setMinimumWidth(100)
        grid_gap_row.addWidget(self.grid_gap_spin)
        grid_gap_row.addStretch()
        cols_form.addLayout(grid_gap_row)

        grid_bg_row = QHBoxLayout()
        grid_bg_row.addWidget(QLabel("背景色："))
        self.grid_bg_combo = QComboBox()
        self.grid_bg_combo.addItem("白色", BackgroundColor.WHITE)
        self.grid_bg_combo.addItem("黑色", BackgroundColor.BLACK)
        self.grid_bg_combo.addItem("透明", BackgroundColor.TRANSPARENT)
        self.grid_bg_combo.setMinimumWidth(120)
        grid_bg_row.addWidget(self.grid_bg_combo)

        self.grid_color_preview = QLabel("    ")
        self.grid_color_preview.setFixedSize(30, 20)
        self.grid_color_preview.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                background: white;
            }
        """)
        grid_bg_row.addWidget(self.grid_color_preview)
        grid_bg_row.addStretch()
        cols_form.addLayout(grid_bg_row)

        grid_layout.addWidget(cols_group)

        hint_label = QLabel("提示：适合制作档案索引封面或胶片式预览")
        hint_label.setStyleSheet("color: #909399; font-size: 12px;")
        grid_layout.addWidget(hint_label)

        grid_layout.addStretch()

        self.mode_stack.addWidget(self.long_page)
        self.mode_stack.addWidget(self.grid_page)

        content_layout.addWidget(self.mode_stack, 1)
        layout.addWidget(self.content_frame, 1)

    def _connect_signals(self):
        self.enable_check.toggled.connect(self._on_enable_toggled)

        self.single_long_radio.toggled.connect(self._on_mode_changed)
        self.cross_long_radio.toggled.connect(self._on_mode_changed)
        self.grid_radio.toggled.connect(self._on_mode_changed)

        self.vertical_radio.toggled.connect(self._on_direction_changed)
        self.horizontal_radio.toggled.connect(self._on_direction_changed)

        self.gap_spin.valueChanged.connect(self._emit_changed)

        self.bg_combo.currentIndexChanged.connect(self._on_bg_changed)

        self.center_radio.toggled.connect(self._on_strategy_changed)
        self.stretch_radio.toggled.connect(self._on_strategy_changed)

        self.cols_spin.valueChanged.connect(self._emit_changed)
        self.cell_width_spin.valueChanged.connect(self._emit_changed)
        self.grid_gap_spin.valueChanged.connect(self._emit_changed)
        self.grid_bg_combo.currentIndexChanged.connect(self._on_grid_bg_changed)

    def _on_enable_toggled(self, checked: bool):
        self._settings.enabled = checked
        self._update_enabled()
        self._emit_changed()

    def _update_enabled(self):
        enabled = self.enable_check.isChecked()
        self.content_frame.setEnabled(enabled)

    def _on_mode_changed(self):
        if self.single_long_radio.isChecked():
            self._settings.mode = OutputMode.SINGLE_LONG_IMAGE
            self.mode_stack.setCurrentWidget(self.long_page)
        elif self.cross_long_radio.isChecked():
            self._settings.mode = OutputMode.CROSS_FILE_LONG_IMAGE
            self.mode_stack.setCurrentWidget(self.long_page)
        elif self.grid_radio.isChecked():
            self._settings.mode = OutputMode.THUMBNAIL_GRID
            self.mode_stack.setCurrentWidget(self.grid_page)
        self._emit_changed()

    def _update_mode_ui(self):
        if self._settings.mode == OutputMode.SINGLE_LONG_IMAGE:
            self.single_long_radio.setChecked(True)
            self.mode_stack.setCurrentWidget(self.long_page)
        elif self._settings.mode == OutputMode.CROSS_FILE_LONG_IMAGE:
            self.cross_long_radio.setChecked(True)
            self.mode_stack.setCurrentWidget(self.long_page)
        elif self._settings.mode == OutputMode.THUMBNAIL_GRID:
            self.grid_radio.setChecked(True)
            self.mode_stack.setCurrentWidget(self.grid_page)

    def _on_direction_changed(self):
        if self.vertical_radio.isChecked():
            self._settings.direction = StitchDirection.VERTICAL
        else:
            self._settings.direction = StitchDirection.HORIZONTAL
        self._emit_changed()

    def _on_bg_changed(self, index: int):
        bg_color = self.bg_combo.currentData()
        self._settings.bg_color = bg_color
        self._update_color_preview(self.color_preview, bg_color)
        self._emit_changed()

    def _on_grid_bg_changed(self, index: int):
        bg_color = self.grid_bg_combo.currentData()
        self._settings.grid_settings.bg_color = bg_color
        self._update_color_preview(self.grid_color_preview, bg_color)
        self._emit_changed()

    def _update_color_preview(self, label: QLabel, bg_color: BackgroundColor):
        if bg_color == BackgroundColor.WHITE:
            label.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    background: white;
                }
            """)
        elif bg_color == BackgroundColor.BLACK:
            label.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    background: black;
                }
            """)
        elif bg_color == BackgroundColor.TRANSPARENT:
            label.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    background: 
                        linear-gradient(45deg, #ccc 25%, transparent 25%),
                        linear-gradient(-45deg, #ccc 25%, transparent 25%),
                        linear-gradient(45deg, transparent 75%, #ccc 75%),
                        linear-gradient(-45deg, transparent 75%, #ccc 75%);
                    background-size: 10px 10px;
                    background-position: 0 0, 0 5px, 5px -5px, -5px 0px;
                }
            """)

    def _on_strategy_changed(self):
        if self.center_radio.isChecked():
            self._settings.width_strategy = WidthStrategy.CENTER
            self._settings.height_strategy = HeightStrategy.CENTER
        else:
            self._settings.width_strategy = WidthStrategy.STRETCH
            self._settings.height_strategy = HeightStrategy.STRETCH
        self._emit_changed()

    def _emit_changed(self):
        self._settings.gap = self.gap_spin.value()
        self._settings.grid_settings.columns = self.cols_spin.value()
        self._settings.grid_settings.cell_width = self.cell_width_spin.value()
        self._settings.grid_settings.gap = self.grid_gap_spin.value()
        self.settingsChanged.emit(self._settings)

    def get_settings(self) -> StitchSettings:
        return self._settings
