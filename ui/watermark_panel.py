from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QSpinBox, QComboBox, QCheckBox,
    QSlider, QColorDialog, QFileDialog, QRadioButton, QButtonGroup,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from core.image_processor import (
    WatermarkSettings, WatermarkType, WatermarkPosition,
    TextWatermarkConfig, ImageWatermarkConfig
)


class WatermarkPanel(QWidget):
    settingsChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = WatermarkSettings()
        self._color_qt = QColor(0, 0, 0)
        self._init_ui()
        self._connect_signals()
        self._update_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("水印设置")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        layout.addWidget(title)

        self.enable_check = QCheckBox("启用水印")
        self.enable_check.setChecked(False)
        layout.addWidget(self.enable_check)

        type_group = QGroupBox("水印类型")
        type_group.setStyleSheet("""
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
        type_layout = QHBoxLayout(type_group)

        self.text_radio = QRadioButton("文字水印")
        self.text_radio.setChecked(True)
        type_layout.addWidget(self.text_radio)

        self.image_radio = QRadioButton("图片水印")
        type_layout.addWidget(self.image_radio)

        type_layout.addStretch()
        layout.addWidget(type_group)

        self._init_text_panel()
        self._init_image_panel()

        common_group = QGroupBox("通用设置")
        common_group.setStyleSheet("""
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
        common_layout = QVBoxLayout(common_group)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("位置:"))
        self.position_combo = QComboBox()
        self.position_combo.addItem("左上角", WatermarkPosition.TOP_LEFT)
        self.position_combo.addItem("右上角", WatermarkPosition.TOP_RIGHT)
        self.position_combo.addItem("左下角", WatermarkPosition.BOTTOM_LEFT)
        self.position_combo.addItem("右下角", WatermarkPosition.BOTTOM_RIGHT)
        self.position_combo.addItem("居中", WatermarkPosition.CENTER)
        self.position_combo.addItem("平铺全屏", WatermarkPosition.TILED)
        self.position_combo.setCurrentIndex(3)
        pos_layout.addWidget(self.position_combo, 1)
        common_layout.addLayout(pos_layout)

        margin_layout = QHBoxLayout()
        margin_layout.addWidget(QLabel("边距:"))
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 500)
        self.margin_spin.setValue(20)
        self.margin_spin.setSuffix(" px")
        margin_layout.addWidget(self.margin_spin)
        margin_layout.addStretch()
        common_layout.addLayout(margin_layout)

        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(50)
        opacity_layout.addWidget(self.opacity_slider, 1)
        self.opacity_value = QLabel("50%")
        self.opacity_value.setMinimumWidth(40)
        self.opacity_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.opacity_value.setStyleSheet("color: #409eff; font-weight: bold;")
        opacity_layout.addWidget(self.opacity_value)
        common_layout.addLayout(opacity_layout)

        self.tile_container = QFrame()
        tile_layout = QVBoxLayout(self.tile_container)
        tile_layout.setContentsMargins(0, 0, 0, 0)

        tile_h_layout = QHBoxLayout()
        tile_h_layout.addWidget(QLabel("平铺间距:"))
        self.tile_x_spin = QSpinBox()
        self.tile_x_spin.setRange(10, 1000)
        self.tile_x_spin.setValue(200)
        self.tile_x_spin.setSuffix(" px")
        tile_h_layout.addWidget(self.tile_x_spin)
        tile_h_layout.addWidget(QLabel("×"))
        self.tile_y_spin = QSpinBox()
        self.tile_y_spin.setRange(10, 1000)
        self.tile_y_spin.setValue(150)
        self.tile_y_spin.setSuffix(" px")
        tile_h_layout.addWidget(self.tile_y_spin)
        tile_h_layout.addStretch()
        tile_layout.addLayout(tile_h_layout)

        common_layout.addWidget(self.tile_container)

        layout.addWidget(common_group)

        config_group = QGroupBox("配置管理")
        config_group.setStyleSheet("""
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
        config_layout = QHBoxLayout(config_group)

        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.setStyleSheet("""
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
        config_layout.addWidget(self.save_config_btn)

        self.load_config_btn = QPushButton("加载配置")
        self.load_config_btn.setStyleSheet("""
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
        config_layout.addWidget(self.load_config_btn)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #f56c6c;
                border-color: #fbc4c4;
                background: #fef0f0;
            }
        """)
        config_layout.addWidget(self.reset_btn)

        layout.addWidget(config_group)

        layout.addStretch()

    def _init_text_panel(self):
        self.text_group = QGroupBox("文字水印设置")
        self.text_group.setStyleSheet("""
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
        text_layout = QVBoxLayout(self.text_group)

        content_layout = QHBoxLayout()
        content_layout.addWidget(QLabel("文字:"))
        self.text_edit = QLineEdit("水印文字")
        content_layout.addWidget(self.text_edit, 1)
        text_layout.addLayout(content_layout)

        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("字体:"))
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Arial", "Times New Roman", "Courier New", "SimHei", "SimSun", "Microsoft YaHei"])
        self.font_combo.setEditable(True)
        font_layout.addWidget(self.font_combo, 1)

        font_layout.addWidget(QLabel("大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 500)
        self.font_size_spin.setValue(36)
        self.font_size_spin.setSuffix(" px")
        font_layout.addWidget(self.font_size_spin)
        text_layout.addLayout(font_layout)

        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("颜色:"))
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(60, 28)
        self.color_btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #dcdfe6;
                border-radius: 4px;
                background: black;
            }
            QPushButton:hover {
                border-color: #409eff;
            }
        """)
        color_layout.addWidget(self.color_btn)

        self.color_value = QColor(0, 0, 0)
        color_layout.addStretch()
        text_layout.addLayout(color_layout)

        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("旋转:"))
        self.rotation_slider = QSlider(Qt.Orientation.Horizontal)
        self.rotation_slider.setRange(-180, 180)
        self.rotation_slider.setValue(0)
        rotation_layout.addWidget(self.rotation_slider, 1)
        self.rotation_value = QLabel("0°")
        self.rotation_value.setMinimumWidth(40)
        self.rotation_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotation_value.setStyleSheet("color: #409eff; font-weight: bold;")
        rotation_layout.addWidget(self.rotation_value)
        text_layout.addLayout(rotation_layout)

        self.layout().addWidget(self.text_group)

    def _init_image_panel(self):
        self.image_group = QGroupBox("图片水印设置")
        self.image_group.setStyleSheet("""
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
        image_layout = QVBoxLayout(self.image_group)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("图片:"))
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText("选择水印图片...")
        path_layout.addWidget(self.image_path_edit, 1)

        self.browse_image_btn = QPushButton("浏览...")
        self.browse_image_btn.setStyleSheet("""
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
        path_layout.addWidget(self.browse_image_btn)
        image_layout.addLayout(path_layout)

        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("缩放:"))
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(1, 200)
        self.scale_slider.setValue(100)
        scale_layout.addWidget(self.scale_slider, 1)
        self.scale_value = QLabel("100%")
        self.scale_value.setMinimumWidth(50)
        self.scale_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scale_value.setStyleSheet("color: #409eff; font-weight: bold;")
        scale_layout.addWidget(self.scale_value)
        image_layout.addLayout(scale_layout)

        self.layout().addWidget(self.image_group)
        self.image_group.setVisible(False)

    def _connect_signals(self):
        self.enable_check.toggled.connect(self._on_enabled_changed)

        self.text_radio.toggled.connect(self._on_type_changed)

        self.text_edit.textChanged.connect(self._emit_changed)
        self.font_combo.currentTextChanged.connect(self._emit_changed)
        self.font_size_spin.valueChanged.connect(self._emit_changed)
        self.color_btn.clicked.connect(self._on_color_clicked)
        self.rotation_slider.valueChanged.connect(self._on_rotation_changed)

        self.image_path_edit.textChanged.connect(self._emit_changed)
        self.browse_image_btn.clicked.connect(self._on_browse_image)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)

        self.position_combo.currentIndexChanged.connect(self._on_position_changed)
        self.margin_spin.valueChanged.connect(self._emit_changed)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.tile_x_spin.valueChanged.connect(self._emit_changed)
        self.tile_y_spin.valueChanged.connect(self._emit_changed)

        self.save_config_btn.clicked.connect(self._on_save_config)
        self.load_config_btn.clicked.connect(self._on_load_config)
        self.reset_btn.clicked.connect(self._on_reset)

    def _on_enabled_changed(self, checked: bool):
        self._settings.enabled = checked
        self._update_ui()
        self._emit_changed()

    def _on_type_changed(self):
        if self.text_radio.isChecked():
            self._settings.type = WatermarkType.TEXT
            self.text_group.setVisible(True)
            self.image_group.setVisible(False)
        else:
            self._settings.type = WatermarkType.IMAGE
            self.text_group.setVisible(False)
            self.image_group.setVisible(True)
        self._emit_changed()

    def _on_color_clicked(self):
        color = QColorDialog.getColor(self._color_qt, self, "选择水印颜色")
        if color.isValid():
            self._color_qt = color
            self.color_btn.setStyleSheet(f"""
                QPushButton {{
                    border: 2px solid #dcdfe6;
                    border-radius: 4px;
                    background: {color.name()};
                }}
                QPushButton:hover {{
                    border-color: #409eff;
                }}
            """)
            self._emit_changed()

    def _on_rotation_changed(self, value: int):
        self.rotation_value.setText(f"{value}°")
        self._emit_changed()

    def _on_browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择水印图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if file_path:
            self.image_path_edit.setText(file_path)

    def _on_scale_changed(self, value: int):
        self.scale_value.setText(f"{value}%")
        self._emit_changed()

    def _on_opacity_changed(self, value: int):
        self.opacity_value.setText(f"{value}%")
        self._emit_changed()

    def _on_position_changed(self, index: int):
        pos = self.position_combo.currentData()
        is_tiled = pos == WatermarkPosition.TILED
        self.tile_container.setVisible(is_tiled)
        self._emit_changed()

    def _on_save_config(self):
        import json
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存水印配置", "watermark_config.json",
            "配置文件 (*.json)"
        )
        if file_path:
            config_data = self._get_settings_dict()
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                pass

    def _on_load_config(self):
        import json
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载水印配置", "",
            "配置文件 (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._apply_settings_dict(data)
                self._update_ui_from_settings()
                self._emit_changed()
            except Exception as e:
                pass

    def _on_reset(self):
        self._settings = WatermarkSettings()
        self._update_ui_from_settings()
        self._emit_changed()

    def _get_settings_dict(self) -> dict:
        return {
            "enabled": self._settings.enabled,
            "type": self._settings.type.value,
            "text_config": {
                "text": self._settings.text_config.text,
                "font_size": self._settings.text_config.font_size,
                "font_family": self._settings.text_config.font_family,
                "color": list(self._settings.text_config.color),
                "opacity": self._settings.text_config.opacity,
                "rotation": self._settings.text_config.rotation,
                "position": self._settings.text_config.position.value,
                "margin": self._settings.text_config.margin,
                "tile_spacing_x": self._settings.text_config.tile_spacing_x,
                "tile_spacing_y": self._settings.text_config.tile_spacing_y,
            },
            "image_config": {
                "image_path": self._settings.image_config.image_path,
                "opacity": self._settings.image_config.opacity,
                "position": self._settings.image_config.position.value,
                "margin": self._settings.image_config.margin,
                "scale": self._settings.image_config.scale,
                "tile_spacing_x": self._settings.image_config.tile_spacing_x,
                "tile_spacing_y": self._settings.image_config.tile_spacing_y,
            }
        }

    def _apply_settings_dict(self, data: dict):
        self._settings.enabled = data.get("enabled", False)
        self._settings.type = WatermarkType(data.get("type", "text"))

        text_data = data.get("text_config", {})
        tc = self._settings.text_config
        tc.text = text_data.get("text", "水印文字")
        tc.font_size = text_data.get("font_size", 36)
        tc.font_family = text_data.get("font_family", "Arial")
        color_list = text_data.get("color", [0, 0, 0, 128])
        tc.color = tuple(color_list) if len(color_list) == 4 else (0, 0, 0, 128)
        tc.opacity = text_data.get("opacity", 128)
        tc.rotation = text_data.get("rotation", 0.0)
        tc.position = WatermarkPosition(text_data.get("position", "bottom_right"))
        tc.margin = text_data.get("margin", 20)
        tc.tile_spacing_x = text_data.get("tile_spacing_x", 200)
        tc.tile_spacing_y = text_data.get("tile_spacing_y", 150)

        image_data = data.get("image_config", {})
        ic = self._settings.image_config
        ic.image_path = image_data.get("image_path", "")
        ic.opacity = image_data.get("opacity", 0.5)
        ic.position = WatermarkPosition(image_data.get("position", "bottom_right"))
        ic.margin = image_data.get("margin", 20)
        ic.scale = image_data.get("scale", 1.0)
        ic.tile_spacing_x = image_data.get("tile_spacing_x", 200)
        ic.tile_spacing_y = image_data.get("tile_spacing_y", 150)

    def _update_ui_from_settings(self):
        self.enable_check.setChecked(self._settings.enabled)

        if self._settings.type == WatermarkType.TEXT:
            self.text_radio.setChecked(True)
        else:
            self.image_radio.setChecked(True)

        tc = self._settings.text_config
        self.text_edit.setText(tc.text)
        self.font_combo.setCurrentText(tc.font_family)
        self.font_size_spin.setValue(tc.font_size)
        self._color_qt = QColor(tc.color[0], tc.color[1], tc.color[2])
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                border: 2px solid #dcdfe6;
                border-radius: 4px;
                background: {self._color_qt.name()};
            }}
            QPushButton:hover {{
                border-color: #409eff;
            }}
        """)
        self.rotation_slider.setValue(int(tc.rotation))

        ic = self._settings.image_config
        self.image_path_edit.setText(ic.image_path)
        self.scale_slider.setValue(int(ic.scale * 100))

        active_config = self._settings.get_active_config()
        pos = active_config.position
        index = self.position_combo.findData(pos)
        if index >= 0:
            self.position_combo.setCurrentIndex(index)
        self.margin_spin.setValue(active_config.margin)

        if self._settings.type == WatermarkType.TEXT:
            opacity_value = int(tc.opacity / 255 * 100)
        else:
            opacity_value = int(ic.opacity * 100)
        self.opacity_slider.setValue(opacity_value)

        self.tile_x_spin.setValue(active_config.tile_spacing_x)
        self.tile_y_spin.setValue(active_config.tile_spacing_y)

        self.tile_container.setVisible(pos == WatermarkPosition.TILED)

    def _update_ui(self):
        enabled = self._settings.enabled
        self.text_group.setEnabled(enabled)
        self.image_group.setEnabled(enabled)

    def _emit_changed(self):
        tc = self._settings.text_config
        tc.text = self.text_edit.text()
        tc.font_family = self.font_combo.currentText()
        tc.font_size = self.font_size_spin.value()
        color = self._color_qt
        tc.color = (color.red(), color.green(), color.blue(), tc.opacity)
        tc.rotation = float(self.rotation_slider.value())
        tc.position = self.position_combo.currentData()
        tc.margin = self.margin_spin.value()
        tc.tile_spacing_x = self.tile_x_spin.value()
        tc.tile_spacing_y = self.tile_y_spin.value()
        opacity_pct = self.opacity_slider.value()
        tc.opacity = int(opacity_pct / 100 * 255)

        ic = self._settings.image_config
        ic.image_path = self.image_path_edit.text()
        ic.scale = self.scale_slider.value() / 100.0
        ic.position = self.position_combo.currentData()
        ic.margin = self.margin_spin.value()
        ic.tile_spacing_x = self.tile_x_spin.value()
        ic.tile_spacing_y = self.tile_y_spin.value()
        ic.opacity = opacity_pct / 100.0

        self.settingsChanged.emit(self._settings)

    def get_settings(self) -> WatermarkSettings:
        return self._settings

    def set_settings(self, settings: WatermarkSettings):
        self._settings = settings
        self._update_ui_from_settings()
