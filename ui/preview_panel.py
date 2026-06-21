from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSplitter, QToolBar, QSpinBox,
    QCheckBox, QSizePolicy, QSlider
)
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QSize
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QBrush,
    QMouseEvent, QWheelEvent
)
from PIL import Image
import io
from typing import Optional

from core.image_converter import format_file_size


class ImageView(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self._pixmap: Optional[QPixmap] = None
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self._last_mouse_pos: Optional[QPoint] = None
        self._is_panning = False
        self._show_1to1 = False
        self._zoom_pos: Optional[QPoint] = None
        self._zoom_factor = 4.0
        self.setMinimumHeight(300)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: #f5f5f5;")

    def set_image(self, pil_image: Optional[Image.Image]):
        if pil_image is None:
            self._pixmap = None
        else:
            buf = io.BytesIO()
            pil_image.save(buf, format='PNG')
            buf.seek(0)
            qimg = QImage.fromData(buf.getvalue())
            self._pixmap = QPixmap.fromImage(qimg)
            self._fit_to_window()
        self.update()

    def set_scale(self, scale: float):
        self._scale = max(0.05, min(scale, 10.0))
        self.update()

    def get_scale(self) -> float:
        return self._scale

    def set_1to1_mode(self, enabled: bool):
        self._show_1to1 = enabled
        self.update()

    def _fit_to_window(self):
        if self._pixmap is None:
            return
        if self._pixmap.width() == 0 or self._pixmap.height() == 0:
            return
        scale_x = (self.width() - 20) / self._pixmap.width()
        scale_y = (self.height() - 20) / self._pixmap.height()
        self._scale = min(scale_x, scale_y, 1.0)
        self._offset = QPoint(0, 0)

    def resizeEvent(self, event):
        if self._pixmap and self._scale < 1.0:
            self._fit_to_window()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if self._pixmap is None:
            painter.setPen(QColor("#999"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                           f"{self.title}\n\n暂无图像")
            return

        painter.fillRect(self.rect(), QColor("#f5f5f5"))

        scaled_w = self._pixmap.width() * self._scale
        scaled_h = self._pixmap.height() * self._scale

        x = (self.width() - scaled_w) / 2 + self._offset.x()
        y = (self.height() - scaled_h) / 2 + self._offset.y()

        painter.drawPixmap(
            int(x), int(y), int(scaled_w), int(scaled_h),
            self._pixmap
        )

        if self._show_1to1 and self._zoom_pos:
            self._draw_zoom_lens(painter, x, y, scaled_w, scaled_h)

        painter.setPen(QColor("#666"))
        painter.drawText(10, 20, 
                        f"{self.title}  |  {self._pixmap.width()}×{self._pixmap.height()} px  |  {self._scale*100:.0f}%")

    def _draw_zoom_lens(self, painter: QPainter, img_x: float, img_y: float, 
                        scaled_w: float, scaled_h: float):
        mouse_pos = self._zoom_pos
        img_mouse_x = (mouse_pos.x() - img_x - self._offset.x()) / self._scale
        img_mouse_y = (mouse_pos.y() - img_y - self._offset.y()) / self._scale

        if (img_mouse_x < 0 or img_mouse_x >= self._pixmap.width() or
            img_mouse_y < 0 or img_mouse_y >= self._pixmap.height()):
            return

        lens_size = 150
        half_lens = lens_size // 2

        source_size = lens_size / self._zoom_factor
        half_source = source_size / 2

        src_x = max(0, min(self._pixmap.width() - source_size, img_mouse_x - half_source))
        src_y = max(0, min(self._pixmap.height() - source_size, img_mouse_y - half_source))

        lens_x = mouse_pos.x() - half_lens
        lens_y = mouse_pos.y() - half_lens

        lens_x = max(10, min(self.width() - lens_size - 10, lens_x))
        lens_y = max(10, min(self.height() - lens_size - 10, lens_y))

        painter.setPen(QPen(QColor("#fff"), 2))
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.drawRoundedRect(int(lens_x), int(lens_y), lens_size, lens_size, 8, 8)

        target_rect = QRect(int(lens_x) + 2, int(lens_y) + 2, 
                           lens_size - 4, lens_size - 4)
        source_rect = QRect(int(src_x), int(src_y), 
                           int(source_size), int(source_size))

        painter.drawPixmap(target_rect, self._pixmap, source_rect)

        painter.setPen(QPen(QColor("#fff"), 1))
        painter.drawLine(int(lens_x + lens_size/2), int(lens_y + 5),
                        int(lens_x + lens_size/2), int(lens_y + lens_size - 5))
        painter.drawLine(int(lens_x + 5), int(lens_y + lens_size/2),
                        int(lens_x + lens_size - 5), int(lens_y + lens_size/2))

        info_text = f"{int(src_x + source_size/2)}, {int(src_y + source_size/2)} px"
        painter.setPen(QColor("#fff"))
        painter.drawText(int(lens_x), int(lens_y + lens_size + 18), info_text)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._last_mouse_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        self._zoom_pos = pos

        if self._is_panning and self._last_mouse_pos:
            delta = pos - self._last_mouse_pos
            self._offset += delta
            self._last_mouse_pos = pos
        self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if self._pixmap is None:
            return

        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        self.set_scale(self._scale * factor)
        super().wheelEvent(event)

    def fit_to_window(self):
        self._fit_to_window()
        self.update()

    def actual_size(self):
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self.update()

    def zoom_in(self):
        self.set_scale(self._scale * 1.25)

    def zoom_out(self):
        self.set_scale(self._scale / 1.25)


class PreviewPanel(QWidget):
    pageChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = 0
        self._total_pages = 0
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title_layout = QHBoxLayout()
        title = QLabel("预览")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        title_layout.addWidget(title)
        title_layout.addStretch()

        self.page_label = QLabel("第 0 / 0 页")
        self.page_label.setStyleSheet("color: #606266;")
        title_layout.addWidget(self.page_label)

        self.prev_btn = QPushButton("◀ 上一页")
        self.prev_btn.setEnabled(False)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover:!disabled {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
            QPushButton:disabled {
                color: #c0c4cc;
                background: #f5f7fa;
            }
        """)
        title_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("下一页 ▶")
        self.next_btn.setEnabled(False)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover:!disabled {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
            QPushButton:disabled {
                color: #c0c4cc;
                background: #f5f7fa;
            }
        """)
        title_layout.addWidget(self.next_btn)

        layout.addLayout(title_layout)

        toolbar = QHBoxLayout()

        self.fit_btn = QPushButton("适应窗口")
        self.fit_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
        """)
        toolbar.addWidget(self.fit_btn)

        self.actual_btn = QPushButton("实际大小")
        self.actual_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
        """)
        toolbar.addWidget(self.actual_btn)

        self.zoom_out_btn = QPushButton("缩小")
        self.zoom_out_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
        """)
        toolbar.addWidget(self.zoom_out_btn)

        self.zoom_in_btn = QPushButton("放大")
        self.zoom_in_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background: #ecf5ff;
            }
        """)
        toolbar.addWidget(self.zoom_in_btn)

        toolbar.addSpacing(20)

        self.pixel_check = QCheckBox("1:1 像素对比（鼠标悬停放大）")
        self.pixel_check.setStyleSheet("""
            QCheckBox {
                spacing: 6px;
                color: #606266;
                font-size: 12px;
            }
        """)
        toolbar.addWidget(self.pixel_check)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #e4e7ed;
                width: 2px;
            }
        """)

        self.original_view = ImageView("原始 PDF")
        self.output_view = ImageView("转换输出")

        splitter.addWidget(self.original_view)
        splitter.addWidget(self.output_view)
        splitter.setSizes([1, 1])

        layout.addWidget(splitter, 1)

        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_frame.setStyleSheet("""
            QFrame {
                background: #f5f7fa;
                border: 1px solid #ebeef5;
                border-radius: 4px;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(20)

        self.info_original = QLabel("原始：-")
        self.info_original.setStyleSheet("color: #606266; font-size: 12px;")
        info_layout.addWidget(self.info_original)

        self.info_output = QLabel("输出：-")
        self.info_output.setStyleSheet("color: #606266; font-size: 12px;")
        info_layout.addWidget(self.info_output)

        info_layout.addStretch()
        layout.addWidget(info_frame)

    def _connect_signals(self):
        self.prev_btn.clicked.connect(self._on_prev_page)
        self.next_btn.clicked.connect(self._on_next_page)
        self.fit_btn.clicked.connect(self._on_fit)
        self.actual_btn.clicked.connect(self._on_actual)
        self.zoom_in_btn.clicked.connect(self._on_zoom_in)
        self.zoom_out_btn.clicked.connect(self._on_zoom_out)
        self.pixel_check.toggled.connect(self._on_pixel_toggled)

    def set_images(self, original_img: Optional[Image.Image], 
                   output_img: Optional[Image.Image],
                   output_info=None):
        self.original_view.set_image(original_img)
        self.output_view.set_image(output_img)

        if original_img:
            self.info_original.setText(
                f"原始：{original_img.width}×{original_img.height} px"
            )
        else:
            self.info_original.setText("原始：-")

        if output_info and output_img:
            size_str = format_file_size(output_info.file_size)
            self.info_output.setText(
                f"输出：{output_img.width}×{output_img.height} px  |  "
                f"{output_info.format}  |  {output_info.dpi} DPI  |  "
                f"预估 {size_str}"
            )
        elif output_img:
            self.info_output.setText(
                f"输出：{output_img.width}×{output_img.height} px"
            )
        else:
            self.info_output.setText("输出：-")

    def set_page_info(self, current: int, total: int):
        self._current_page = current
        self._total_pages = total
        self.page_label.setText(f"第 {current} / {total} 页")
        self.prev_btn.setEnabled(current > 1)
        self.next_btn.setEnabled(current < total)

    def _on_prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.pageChanged.emit(self._current_page)
            self.set_page_info(self._current_page, self._total_pages)

    def _on_next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self.pageChanged.emit(self._current_page)
            self.set_page_info(self._current_page, self._total_pages)

    def _on_fit(self):
        self.original_view.fit_to_window()
        self.output_view.fit_to_window()

    def _on_actual(self):
        self.original_view.actual_size()
        self.output_view.actual_size()

    def _on_zoom_in(self):
        self.original_view.zoom_in()
        self.output_view.zoom_in()

    def _on_zoom_out(self):
        self.original_view.zoom_out()
        self.output_view.zoom_out()

    def _on_pixel_toggled(self, checked: bool):
        self.original_view.set_1to1_mode(checked)
        self.output_view.set_1to1_mode(checked)
