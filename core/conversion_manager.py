import os
from typing import List, Optional, Callable
from dataclasses import dataclass, field
from PIL import Image

from .pdf_parser import PdfParser, PdfMetadata
from .image_converter import (
    ImageConverter, ConversionSettings, OutputInfo,
    OutputFormat, ColorSpace
)
from .image_stitcher import (
    ImageStitcher, StitchDirection, BackgroundColor,
    WidthStrategy, HeightStrategy
)
from enum import Enum
from .file_namer import PageRangeParser, NamingTemplate, OutputOrganizer


class OutputMode(Enum):
    NORMAL_PAGES = "normal"
    SINGLE_LONG_IMAGE = "single_long"
    CROSS_FILE_LONG_IMAGE = "cross_long"
    THUMBNAIL_GRID = "grid"


@dataclass
class GridSettings:
    columns: int = 3
    gap: int = 10
    bg_color: BackgroundColor = BackgroundColor.WHITE
    cell_width: int = 400


@dataclass
class PdfItem:
    file_path: str
    metadata: Optional[PdfMetadata] = None
    password: str = ""
    is_loaded: bool = False
    is_error: bool = False
    error_message: str = ""

    @property
    def file_name(self) -> str:
        return os.path.basename(self.file_path)


@dataclass
class StitchSettings:
    enabled: bool = False
    mode: OutputMode = OutputMode.SINGLE_LONG_IMAGE
    direction: StitchDirection = StitchDirection.VERTICAL
    gap: int = 0
    bg_color: BackgroundColor = BackgroundColor.WHITE
    width_strategy: WidthStrategy = WidthStrategy.CENTER
    height_strategy: HeightStrategy = HeightStrategy.CENTER
    grid_settings: GridSettings = field(default_factory=GridSettings)


@dataclass
class ExportSettings:
    output_dir: str = ""
    naming_template: str = "[原文件名]_第[页码]页"
    page_range: str = ""
    create_subfolder: bool = True
    stitch_settings: StitchSettings = field(default_factory=StitchSettings)


@dataclass
class ConversionResult:
    pdf_item: PdfItem
    success: bool
    output_files: List[str] = field(default_factory=list)
    error_message: str = ""
    output_infos: List[OutputInfo] = field(default_factory=list)
    total_size: int = 0


class ConversionTask:
    def __init__(self,
                 pdf_item: PdfItem,
                 conversion_settings: ConversionSettings,
                 export_settings: ExportSettings):
        self.pdf_item = pdf_item
        self.conversion_settings = conversion_settings
        self.export_settings = export_settings
        self.progress: float = 0.0
        self.result: Optional[ConversionResult] = None
        self._canceled: bool = False

    def cancel(self):
        self._canceled = True

    @property
    def is_canceled(self) -> bool:
        return self._canceled


class ConversionManager:
    def __init__(self):
        self._tasks: List[ConversionTask] = []

    def convert_single(self,
                       task: ConversionTask,
                       progress_callback: Optional[Callable[[float], None]] = None
                       ) -> ConversionResult:
        result = ConversionResult(pdf_item=task.pdf_item, success=False)

        try:
            parser = PdfParser(task.pdf_item.file_path)
            if not parser.open(task.pdf_item.password):
                result.error_message = "无法打开PDF文件"
                task.result = result
                return result

            if not parser.metadata or not parser.metadata.is_valid:
                result.error_message = parser.metadata.error_message if parser.metadata else "无效的PDF文件"
                parser.close()
                task.result = result
                return result

            total_pages = parser.page_count
            pages_to_export = PageRangeParser.parse(
                task.export_settings.page_range, total_pages
            )

            if not pages_to_export:
                result.error_message = "没有可导出的页面"
                parser.close()
                task.result = result
                return result

            stitch_enabled = task.export_settings.stitch_settings.enabled
            stitch_mode = task.export_settings.stitch_settings.mode
            stitch_images = []

            fmt_ext = task.conversion_settings.output_format.value

            for i, page_num in enumerate(pages_to_export):
                if task.is_canceled:
                    result.error_message = "已取消"
                    parser.close()
                    task.result = result
                    return result

                if progress_callback:
                    progress = (i / len(pages_to_export)) * 100
                    progress_callback(progress)

                img = parser.get_page_image(
                    page_num - 1,
                    dpi=task.conversion_settings.dpi
                )

                if img is None:
                    continue

                if stitch_enabled and stitch_mode in (OutputMode.SINGLE_LONG_IMAGE, OutputMode.THUMBNAIL_GRID):
                    stitch_images.append(img)
                else:
                    img = ImageConverter.convert_color_space(
                        img, task.conversion_settings.color_space
                    )

                    file_name = NamingTemplate.generate(
                        task.export_settings.naming_template,
                        task.pdf_item.file_name,
                        page_num,
                        total_pages,
                        task.conversion_settings.dpi,
                        fmt_ext
                    )

                    output_path = OutputOrganizer.get_output_path(
                        task.export_settings.output_dir,
                        f"{file_name}.{fmt_ext}",
                        task.export_settings.create_subfolder,
                        task.pdf_item.file_name
                    )

                    output_path = OutputOrganizer.get_unique_path(output_path)

                    info = ImageConverter.save_image(
                        img, output_path, task.conversion_settings
                    )

                    result.output_files.append(output_path)
                    result.output_infos.append(info)
                    result.total_size += info.file_size

            if stitch_enabled and stitch_images:
                if stitch_mode == OutputMode.THUMBNAIL_GRID:
                    grid_settings = task.export_settings.stitch_settings.grid_settings
                    stitched = ImageStitcher.create_grid(
                        stitch_images,
                        columns=grid_settings.columns,
                        gap=grid_settings.gap,
                        bg_color=grid_settings.bg_color,
                        cell_width=grid_settings.cell_width
                    )
                    suffix = "_缩略图网格"
                else:
                    stitched = ImageStitcher.stitch(
                        stitch_images,
                        direction=task.export_settings.stitch_settings.direction,
                        gap=task.export_settings.stitch_settings.gap,
                        bg_color=task.export_settings.stitch_settings.bg_color,
                        width_strategy=task.export_settings.stitch_settings.width_strategy,
                        height_strategy=task.export_settings.stitch_settings.height_strategy
                    )
                    suffix = "_长图"

                stitched = ImageConverter.convert_color_space(
                    stitched, task.conversion_settings.color_space
                )

                file_name = NamingTemplate.generate(
                    task.export_settings.naming_template,
                    task.pdf_item.file_name,
                    1,
                    1,
                    task.conversion_settings.dpi,
                    fmt_ext
                )

                output_path = OutputOrganizer.get_output_path(
                    task.export_settings.output_dir,
                    f"{file_name}{suffix}.{fmt_ext}",
                    task.export_settings.create_subfolder,
                    task.pdf_item.file_name
                )

                output_path = OutputOrganizer.get_unique_path(output_path)

                info = ImageConverter.save_image(
                    stitched, output_path, task.conversion_settings
                )

                result.output_files.append(output_path)
                result.output_infos.append(info)
                result.total_size += info.file_size

            parser.close()
            result.success = True

        except Exception as e:
            result.error_message = str(e)

        if progress_callback:
            progress_callback(100.0)

        task.result = result
        return result

    def preview_page(self,
                     pdf_item: PdfItem,
                     page_num: int,
                     dpi: int = 150) -> Optional[Image.Image]:
        try:
            parser = PdfParser(pdf_item.file_path)
            if not parser.open(pdf_item.password):
                return None

            img = parser.get_page_image(page_num, dpi=dpi)
            parser.close()
            return img
        except Exception:
            return None

    def preview_converted(self,
                          pdf_item: PdfItem,
                          page_num: int,
                          settings: ConversionSettings) -> Optional[Image.Image]:
        try:
            parser = PdfParser(pdf_item.file_path)
            if not parser.open(pdf_item.password):
                return None

            img = parser.get_page_image(page_num, dpi=settings.dpi)
            parser.close()

            if img is None:
                return None

            img = ImageConverter.convert_color_space(img, settings.color_space)
            img = ImageConverter.prepare_for_format(img, settings.output_format)

            return img
        except Exception:
            return None

    def preview_both(self,
                     pdf_item: PdfItem,
                     page_num: int,
                     settings: ConversionSettings) -> Optional[tuple]:
        try:
            parser = PdfParser(pdf_item.file_path)
            if not parser.open(pdf_item.password):
                return None

            preview_dpi = min(settings.dpi, 150)
            original_img = parser.get_page_image(page_num, dpi=preview_dpi)
            output_img = parser.get_page_image(page_num, dpi=preview_dpi)
            parser.close()

            if original_img is None or output_img is None:
                return None

            output_img = ImageConverter.convert_color_space(output_img, settings.color_space)
            output_img = ImageConverter.prepare_for_format(output_img, settings.output_format)

            return (original_img, output_img)
        except Exception:
            return None

    def estimate_stitch_size(self,
                             pdf_item: PdfItem,
                             conversion_settings: ConversionSettings,
                             export_settings: ExportSettings) -> Optional[dict]:
        try:
            if not export_settings.stitch_settings.enabled:
                return None

            parser = PdfParser(pdf_item.file_path)
            if not parser.open(pdf_item.password):
                return None

            total_pages = parser.page_count
            pages_to_export = PageRangeParser.parse(
                export_settings.page_range, total_pages
            )

            if not pages_to_export:
                parser.close()
                return None

            dpi = conversion_settings.dpi
            stitch_settings = export_settings.stitch_settings
            gap = stitch_settings.gap

            widths = []
            heights = []
            for page_num in pages_to_export:
                w_pt, h_pt = parser.get_page_size_pt(page_num - 1)
                w_px = int(w_pt / 72 * dpi)
                h_px = int(h_pt / 72 * dpi)
                widths.append(w_px)
                heights.append(h_px)

            parser.close()

            num_pages = len(pages_to_export)
            total_gap = gap * (num_pages - 1)

            if stitch_settings.direction == StitchDirection.VERTICAL:
                max_width = max(widths)
                total_height = sum(heights) + total_gap
                final_width = max_width
                final_height = total_height
            else:
                max_height = max(heights)
                total_width = sum(widths) + total_gap
                final_width = total_width
                final_height = max_height

            max_dim = max(final_width, final_height)
            fmt = conversion_settings.output_format

            warnings = []
            if fmt == OutputFormat.JPG and max_dim > 65000:
                warnings.append(
                    f"JPG 格式最大支持 65535 像素，预估尺寸 {max_dim} 像素超出限制"
                )
            if fmt == OutputFormat.WEBP and max_dim > 16383:
                warnings.append(
                    f"WebP 格式最大支持 16383 像素，预估尺寸 {max_dim} 像素超出限制"
                )
            if max_dim > 30000:
                warnings.append(
                    f"预估尺寸过大 ({final_width}x{final_height})，可能导致保存失败或内存不足"
                )

            return {
                "width": final_width,
                "height": final_height,
                "pages": num_pages,
                "warnings": warnings
            }

        except Exception:
            return None

    def estimate_grid_size(self,
                           pdf_item: PdfItem,
                           conversion_settings: ConversionSettings,
                           export_settings: ExportSettings) -> Optional[dict]:
        try:
            if not export_settings.stitch_settings.enabled:
                return None
            if export_settings.stitch_settings.mode != OutputMode.THUMBNAIL_GRID:
                return None

            parser = PdfParser(pdf_item.file_path)
            if not parser.open(pdf_item.password):
                return None

            total_pages = parser.page_count
            pages_to_export = PageRangeParser.parse(
                export_settings.page_range, total_pages
            )

            if not pages_to_export:
                parser.close()
                return None

            dpi = conversion_settings.dpi
            grid_settings = export_settings.stitch_settings.grid_settings
            columns = grid_settings.columns
            gap = grid_settings.gap
            cell_width = grid_settings.cell_width

            col_widths = [0] * columns
            row_heights = []
            current_row_heights = []

            for idx, page_num in enumerate(pages_to_export):
                w_pt, h_pt = parser.get_page_size_pt(page_num - 1)
                w_px = int(w_pt / 72 * dpi)
                h_px = int(h_pt / 72 * dpi)

                if cell_width and cell_width > 0:
                    ratio = cell_width / w_px
                    w_px = cell_width
                    h_px = max(1, int(h_px * ratio))

                col = idx % columns
                if w_px > col_widths[col]:
                    col_widths[col] = w_px

                current_row_heights.append(h_px)
                if (idx + 1) % columns == 0 or idx == len(pages_to_export) - 1:
                    row_heights.append(max(current_row_heights))
                    current_row_heights = []

            parser.close()

            num_rows = len(row_heights)
            total_width = sum(col_widths) + gap * (columns - 1)
            total_height = sum(row_heights) + gap * (num_rows - 1)

            max_dim = max(total_width, total_height)
            fmt = conversion_settings.output_format

            warnings = []
            if fmt == OutputFormat.JPG and max_dim > 65000:
                warnings.append(
                    f"JPG 格式最大支持 65535 像素，预估尺寸 {max_dim} 像素超出限制"
                )
            if fmt == OutputFormat.WEBP and max_dim > 16383:
                warnings.append(
                    f"WebP 格式最大支持 16383 像素，预估尺寸 {max_dim} 像素超出限制"
                )
            if max_dim > 30000:
                warnings.append(
                    f"预估尺寸过大 ({total_width}x{total_height})，可能导致保存失败或内存不足"
                )

            return {
                "width": total_width,
                "height": total_height,
                "pages": len(pages_to_export),
                "columns": columns,
                "rows": num_rows,
                "warnings": warnings
            }

        except Exception:
            return None

    def estimate_cross_file_stitch_size(self,
                                        pdf_items: List[PdfItem],
                                        conversion_settings: ConversionSettings,
                                        export_settings: ExportSettings) -> Optional[dict]:
        try:
            if not export_settings.stitch_settings.enabled:
                return None
            if export_settings.stitch_settings.mode != OutputMode.CROSS_FILE_LONG_IMAGE:
                return None

            dpi = conversion_settings.dpi
            stitch_settings = export_settings.stitch_settings
            gap = stitch_settings.gap

            all_widths = []
            all_heights = []
            total_pages_count = 0

            for pdf_item in pdf_items:
                parser = PdfParser(pdf_item.file_path)
                if not parser.open(pdf_item.password):
                    continue

                total_pages = parser.page_count
                pages_to_export = PageRangeParser.parse(
                    export_settings.page_range, total_pages
                )

                for page_num in pages_to_export:
                    w_pt, h_pt = parser.get_page_size_pt(page_num - 1)
                    w_px = int(w_pt / 72 * dpi)
                    h_px = int(h_pt / 72 * dpi)
                    all_widths.append(w_px)
                    all_heights.append(h_px)
                    total_pages_count += 1

                parser.close()

            if not all_widths:
                return None

            total_gap = gap * (len(all_widths) - 1)

            if stitch_settings.direction == StitchDirection.VERTICAL:
                max_width = max(all_widths)
                total_height = sum(all_heights) + total_gap
                final_width = max_width
                final_height = total_height
            else:
                max_height = max(all_heights)
                total_width = sum(all_widths) + total_gap
                final_width = total_width
                final_height = max_height

            max_dim = max(final_width, final_height)
            fmt = conversion_settings.output_format

            warnings = []
            if fmt == OutputFormat.JPG and max_dim > 65000:
                warnings.append(
                    f"JPG 格式最大支持 65535 像素，预估尺寸 {max_dim} 像素超出限制"
                )
            if fmt == OutputFormat.WEBP and max_dim > 16383:
                warnings.append(
                    f"WebP 格式最大支持 16383 像素，预估尺寸 {max_dim} 像素超出限制"
                )
            if max_dim > 30000:
                warnings.append(
                    f"预估尺寸过大 ({final_width}x{final_height})，可能导致保存失败或内存不足"
                )

            return {
                "width": final_width,
                "height": final_height,
                "pages": total_pages_count,
                "files": len(pdf_items),
                "warnings": warnings
            }

        except Exception:
            return None

    def convert_cross_file_long_image(self,
                                      tasks: List[ConversionTask],
                                      progress_callback: Optional[Callable[[float], None]] = None
                                      ) -> ConversionResult:
        if not tasks:
            result = ConversionResult(
                pdf_item=PdfItem(file_path=""),
                success=False,
                error_message="没有待转换的文件"
            )
            return result

        first_pdf = tasks[0].pdf_item
        result = ConversionResult(pdf_item=first_pdf, success=False)
        all_images = []
        total_pages = 0

        try:
            conversion_settings = tasks[0].conversion_settings
            export_settings = tasks[0].export_settings
            stitch_settings = export_settings.stitch_settings
            fmt_ext = conversion_settings.output_format.value

            for task_idx, task in enumerate(tasks):
                if task.is_canceled:
                    result.error_message = "已取消"
                    task.result = result
                    return result

                parser = PdfParser(task.pdf_item.file_path)
                if not parser.open(task.pdf_item.password):
                    continue

                pdf_total_pages = parser.page_count
                pages_to_export = PageRangeParser.parse(
                    export_settings.page_range, pdf_total_pages
                )

                for i, page_num in enumerate(pages_to_export):
                    if task.is_canceled:
                        parser.close()
                        result.error_message = "已取消"
                        task.result = result
                        return result

                    if progress_callback:
                        overall_idx = total_pages + i
                        total_expected = sum(
                            len(PageRangeParser.parse(export_settings.page_range, PdfParser(t.pdf_item.file_path).page_count))
                            if PdfParser(t.pdf_item.file_path).open(t.pdf_item.password)
                            else 0
                            for t in tasks
                        )
                        if total_expected > 0:
                            progress = (overall_idx / total_expected) * 100
                            progress_callback(progress)

                    img = parser.get_page_image(
                        page_num - 1,
                        dpi=conversion_settings.dpi
                    )

                    if img is not None:
                        all_images.append(img)

                total_pages += len(pages_to_export)
                parser.close()

            if not all_images:
                result.error_message = "没有可导出的页面"
                return result

            stitched = ImageStitcher.stitch(
                all_images,
                direction=stitch_settings.direction,
                gap=stitch_settings.gap,
                bg_color=stitch_settings.bg_color,
                width_strategy=stitch_settings.width_strategy,
                height_strategy=stitch_settings.height_strategy
            )

            stitched = ImageConverter.convert_color_space(
                stitched, conversion_settings.color_space
            )

            first_name = os.path.splitext(first_pdf.file_name)[0]
            base_output_name = f"{first_name}_等{len(tasks)}个文件_跨文件长图"

            output_path = OutputOrganizer.get_output_path(
                export_settings.output_dir,
                f"{base_output_name}.{fmt_ext}",
                False,
                first_pdf.file_name
            )

            output_path = OutputOrganizer.get_unique_path(output_path)

            info = ImageConverter.save_image(
                stitched, output_path, conversion_settings
            )

            result.output_files.append(output_path)
            result.output_infos.append(info)
            result.total_size += info.file_size
            result.success = True

        except Exception as e:
            result.error_message = str(e)

        if progress_callback:
            progress_callback(100.0)

        for task in tasks:
            task.result = result

        return result
