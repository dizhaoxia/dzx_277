from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QSlider, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.image_processor import CropSettings, CropMode


class CropPanel(QWidget):
    settingsChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = CropSettings()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("自动裁剪白边")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        layout.addWidget(title)

        crop_group = QGroupBox("裁剪设置")
        crop_group.setStyleSheet("""
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
        crop_layout = QVBoxLayout(crop_group)

        self.enable_check = QCheckBox("启用自动裁剪白边")
        self.enable_check.setChecked(False)
        crop_layout.addWidget(self.enable_check)

        desc = QLabel("基于边缘像素检测算法智能识别页面四周的空白区域并裁剪，输出干净的内容区图片。")
        desc.setStyleSheet("color: #909399; font-size: 12px;")
        desc.setWordWrap(True)
        crop_layout.addWidget(desc)

        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("白边阈值:"))
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(200, 255)
        self.threshold_slider.setValue(240)
        threshold_layout.addWidget(self.threshold_slider, 1)
        self.threshold_value = QLabel("240")
        self.threshold_value.setMinimumWidth(35)
        self.threshold_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.threshold_value.setStyleSheet("color: #409eff; font-weight: bold;")
        threshold_layout.addWidget(self.threshold_value)
        crop_layout.addLayout(threshold_layout)

        threshold_desc = QLabel("数值越大，越容易被识别为白色（建议 235-245）")
        threshold_desc.setStyleSheet("color: #909399; font-size: 11px;")
        crop_layout.addWidget(threshold_desc)

        padding_layout = QHBoxLayout()
        padding_layout.addWidget(QLabel("内边距:"))
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 200)
        self.padding_spin.setValue(0)
        self.padding_spin.setSuffix(" px")
        padding_layout.addWidget(self.padding_spin)
        padding_layout.addStretch()
        crop_layout.addLayout(padding_layout)

        padding_desc = QLabel("裁剪后保留的额外边距，防止内容被误裁")
        padding_desc.setStyleSheet("color: #909399; font-size: 11px;")
        crop_layout.addWidget(padding_desc)

        layout.addWidget(crop_group)

        tip_group = QGroupBox("使用提示")
        tip_group.setStyleSheet("""
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
        tip_layout = QVBoxLayout(tip_group)

        tips = [
            "• 适用于扫描件、PDF 截图等带有白边的图片",
            "• 调整阈值可以控制识别的灵敏度",
            "• 如果内容被误裁，请降低阈值或增加内边距",
            "• 如果白边未裁干净，请提高阈值",
        ]
        for tip in tips:
            tip_label = QLabel(tip)
            tip_label.setStyleSheet("color: #606266; font-size: 12px;")
            tip_layout.addWidget(tip_label)

        layout.addWidget(tip_group)

        layout.addStretch()

    def _connect_signals(self):
        self.enable_check.toggled.connect(self._on_enabled_changed)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        self.padding_spin.valueChanged.connect(self._emit_changed)

    def _on_enabled_changed(self, checked: bool):
        self._settings.enabled = checked
        if checked:
            self._settings.mode = CropMode.AUTO
        else:
            self._settings.mode = CropMode.DISABLED
        self._emit_changed()

    def _on_threshold_changed(self, value: int):
        self.threshold_value.setText(str(value))
        self._settings.threshold = value
        self._emit_changed()

    def _emit_changed(self):
        self.settingsChanged.emit(self._settings)

    def get_settings(self) -> CropSettings:
        return self._settings

    def set_settings(self, settings: CropSettings):
        self._settings = settings
        self.enable_check.setChecked(settings.enabled)
        self.threshold_slider.setValue(settings.threshold)
        self.threshold_value.setText(str(settings.threshold))
        self.padding_spin.setValue(settings.padding)
