from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QRadioButton, QButtonGroup, QSpinBox, QGroupBox,
    QComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from core.image_stitcher import (
    StitchDirection, BackgroundColor, WidthStrategy, HeightStrategy
)
from core.conversion_manager import StitchSettings


class StitchPanel(QWidget):
    settingsChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = StitchSettings()
        self._init_ui()
        self._connect_signals()
        self._update_enabled()
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
        content_layout.addWidget(direction_group)

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
        content_layout.addWidget(gap_group)

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
        content_layout.addWidget(bg_group)

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

        content_layout.addWidget(align_group)

        content_layout.addStretch()
        layout.addWidget(self.content_frame, 1)

    def _connect_signals(self):
        self.enable_check.toggled.connect(self._on_enable_toggled)
        self.vertical_radio.toggled.connect(self._on_direction_changed)
        self.horizontal_radio.toggled.connect(self._on_direction_changed)
        self.gap_spin.valueChanged.connect(self._emit_changed)
        self.bg_combo.currentIndexChanged.connect(self._on_bg_changed)
        self.center_radio.toggled.connect(self._on_strategy_changed)
        self.stretch_radio.toggled.connect(self._on_strategy_changed)

    def _on_enable_toggled(self, checked: bool):
        self._settings.enabled = checked
        self._update_enabled()
        self._emit_changed()

    def _update_enabled(self):
        enabled = self.enable_check.isChecked()
        self.content_frame.setEnabled(enabled)

    def _on_direction_changed(self):
        if self.vertical_radio.isChecked():
            self._settings.direction = StitchDirection.VERTICAL
        else:
            self._settings.direction = StitchDirection.HORIZONTAL
        self._emit_changed()

    def _on_bg_changed(self, index: int):
        bg_color = self.bg_combo.currentData()
        self._settings.bg_color = bg_color
        self._update_color_preview(bg_color)
        self._emit_changed()

    def _update_color_preview(self, bg_color: BackgroundColor):
        if bg_color == BackgroundColor.WHITE:
            self.color_preview.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    background: white;
                }
            """)
        elif bg_color == BackgroundColor.BLACK:
            self.color_preview.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    background: black;
                }
            """)
        elif bg_color == BackgroundColor.TRANSPARENT:
            self.color_preview.setStyleSheet("""
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
        self.settingsChanged.emit(self._settings)

    def get_settings(self) -> StitchSettings:
        return self._settings
