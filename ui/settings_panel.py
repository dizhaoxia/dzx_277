from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QRadioButton, QComboBox, QSlider, QSpinBox,
    QGroupBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Optional

from core.image_converter import (
    ConversionSettings, OutputFormat, ColorSpace,
    ImageConverter
)
from core.pdf_parser import PdfMetadata


class SettingsPanel(QWidget):
    settingsChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = ConversionSettings()
        self._current_meta: Optional[PdfMetadata] = None
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("输出参数设置")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        layout.addWidget(title)

        format_group = QGroupBox("输出格式")
        format_group.setStyleSheet("""
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
        format_layout = QHBoxLayout(format_group)

        self.png_radio = QRadioButton("PNG")
        self.png_radio.setChecked(True)
        self.png_radio.setStyleSheet("QRadioButton { spacing: 4px; }")
        format_layout.addWidget(self.png_radio)

        self.jpg_radio = QRadioButton("JPG")
        format_layout.addWidget(self.jpg_radio)

        self.webp_radio = QRadioButton("WebP")
        format_layout.addWidget(self.webp_radio)

        format_layout.addStretch()
        layout.addWidget(format_group)

        self.format_desc = QLabel("PNG 格式：支持透明通道，无损压缩")
        self.format_desc.setStyleSheet("color: #909399; font-size: 12px;")
        layout.addWidget(self.format_desc)

        dpi_group = QGroupBox("分辨率 (DPI)")
        dpi_group.setStyleSheet("""
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
        dpi_layout = QVBoxLayout(dpi_group)

        preset_layout = QHBoxLayout()
        self.dpi_150_btn = QPushButton("150")
        self.dpi_300_btn = QPushButton("300")
        self.dpi_600_btn = QPushButton("600")
        self.dpi_custom_btn = QPushButton("自定义")
        self.dpi_custom_btn.setCheckable(True)

        for btn in [self.dpi_150_btn, self.dpi_300_btn, self.dpi_600_btn]:
            btn.setCheckable(True)
            btn.setMinimumWidth(60)
            btn.setStyleSheet("""
                QPushButton {
                    background: white;
                    color: #606266;
                    border: 1px solid #dcdfe6;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background: #409eff;
                    color: white;
                    border-color: #409eff;
                }
                QPushButton:hover:!checked {
                    color: #409eff;
                    border-color: #c6e2ff;
                }
            """)

        self.dpi_150_btn.setChecked(True)
        preset_layout.addWidget(self.dpi_150_btn)
        preset_layout.addWidget(self.dpi_300_btn)
        preset_layout.addWidget(self.dpi_600_btn)
        preset_layout.addWidget(self.dpi_custom_btn)
        preset_layout.addStretch()
        dpi_layout.addLayout(preset_layout)

        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("自定义 DPI："))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(1, 4800)
        self.dpi_spin.setValue(150)
        self.dpi_spin.setEnabled(False)
        self.dpi_spin.setMinimumWidth(100)
        custom_layout.addWidget(self.dpi_spin)
        custom_layout.addStretch()
        dpi_layout.addLayout(custom_layout)

        layout.addWidget(dpi_group)

        color_group = QGroupBox("色彩空间")
        color_group.setStyleSheet("""
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
        color_layout = QVBoxLayout(color_group)

        self.keep_color_radio = QRadioButton("保持原始（CMYK / RGB）")
        self.keep_color_radio.setChecked(True)
        color_layout.addWidget(self.keep_color_radio)

        self.srgb_radio = QRadioButton("强制转换为 sRGB")
        color_layout.addWidget(self.srgb_radio)

        layout.addWidget(color_group)

        self.quality_group = QGroupBox("压缩质量")
        self.quality_group.setStyleSheet("""
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
        quality_layout = QVBoxLayout(self.quality_group)

        slider_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        self.quality_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.quality_slider.setTickInterval(10)
        slider_layout.addWidget(self.quality_slider, 1)

        self.quality_value = QLabel("85")
        self.quality_value.setMinimumWidth(35)
        self.quality_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quality_value.setStyleSheet("font-weight: bold; color: #409eff;")
        slider_layout.addWidget(self.quality_value)

        quality_layout.addLayout(slider_layout)

        self.size_estimate = QLabel("预估单页大小：-")
        self.size_estimate.setStyleSheet("color: #909399; font-size: 12px;")
        quality_layout.addWidget(self.size_estimate)

        layout.addWidget(self.quality_group)
        self.quality_group.setVisible(False)

        layout.addStretch()

    def _connect_signals(self):
        self.png_radio.toggled.connect(self._on_format_changed)
        self.jpg_radio.toggled.connect(self._on_format_changed)
        self.webp_radio.toggled.connect(self._on_format_changed)

        self.dpi_150_btn.clicked.connect(lambda: self._on_dpi_preset(150))
        self.dpi_300_btn.clicked.connect(lambda: self._on_dpi_preset(300))
        self.dpi_600_btn.clicked.connect(lambda: self._on_dpi_preset(600))
        self.dpi_custom_btn.toggled.connect(self._on_custom_dpi_toggled)
        self.dpi_spin.valueChanged.connect(self._on_dpi_changed)

        self.keep_color_radio.toggled.connect(self._on_color_changed)
        self.srgb_radio.toggled.connect(self._on_color_changed)

        self.quality_slider.valueChanged.connect(self._on_quality_changed)

    def _on_format_changed(self):
        if self.png_radio.isChecked():
            self._settings.output_format = OutputFormat.PNG
            self.format_desc.setText("PNG 格式：支持透明通道，无损压缩")
            self.quality_group.setVisible(False)
        elif self.jpg_radio.isChecked():
            self._settings.output_format = OutputFormat.JPG
            self.format_desc.setText("JPG 格式：白底，有损压缩，文件较小")
            self.quality_group.setVisible(True)
        elif self.webp_radio.isChecked():
            self._settings.output_format = OutputFormat.WEBP
            self.format_desc.setText("WebP 格式：兼顾体积与画质，支持透明")
            self.quality_group.setVisible(True)

        self._update_size_estimate()
        self.settingsChanged.emit(self._settings)

    def _on_dpi_preset(self, dpi: int):
        self.dpi_150_btn.setChecked(dpi == 150)
        self.dpi_300_btn.setChecked(dpi == 300)
        self.dpi_600_btn.setChecked(dpi == 600)
        self.dpi_custom_btn.setChecked(False)
        self.dpi_spin.setEnabled(False)
        self.dpi_spin.setValue(dpi)
        self._settings.dpi = dpi
        self._update_size_estimate()
        self.settingsChanged.emit(self._settings)

    def _on_custom_dpi_toggled(self, checked: bool):
        if checked:
            self.dpi_150_btn.setChecked(False)
            self.dpi_300_btn.setChecked(False)
            self.dpi_600_btn.setChecked(False)
            self.dpi_spin.setEnabled(True)
            self._settings.dpi = self.dpi_spin.value()
        self._update_size_estimate()
        self.settingsChanged.emit(self._settings)

    def _on_dpi_changed(self, value: int):
        self._settings.dpi = value
        if not self.dpi_custom_btn.isChecked():
            self.dpi_custom_btn.setChecked(True)
            self.dpi_150_btn.setChecked(False)
            self.dpi_300_btn.setChecked(False)
            self.dpi_600_btn.setChecked(False)
            self.dpi_spin.setEnabled(True)
        self._update_size_estimate()
        self.settingsChanged.emit(self._settings)

    def _on_color_changed(self):
        if self.keep_color_radio.isChecked():
            self._settings.color_space = ColorSpace.KEEP_ORIGINAL
        else:
            self._settings.color_space = ColorSpace.FORCE_SRGB
        self._update_size_estimate()
        self.settingsChanged.emit(self._settings)

    def _on_quality_changed(self, value: int):
        self.quality_value.setText(str(value))
        self._settings.jpg_quality = value
        self._settings.webp_quality = value
        self._update_size_estimate()
        self.settingsChanged.emit(self._settings)

    def _update_size_estimate(self):
        if not self._current_meta:
            return

        width_px = int(self._current_meta.page_width_pt / 72 * self._settings.dpi)
        height_px = int(self._current_meta.page_height_pt / 72 * self._settings.dpi)

        min_size, max_size = ImageConverter.estimate_file_size(
            width_px, height_px, self._settings
        )

        from core.image_converter import format_file_size
        self.size_estimate.setText(
            f"预估单页大小：{format_file_size(min_size)} ~ {format_file_size(max_size)}"
        )

    def set_current_metadata(self, meta: Optional[PdfMetadata]):
        self._current_meta = meta
        self._update_size_estimate()

    def get_settings(self) -> ConversionSettings:
        return self._settings
