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
from .file_namer import PageRangeParser, NamingTemplate, OutputOrganizer


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
    direction: StitchDirection = StitchDirection.VERTICAL
    gap: int = 0
    bg_color: BackgroundColor = BackgroundColor.WHITE
    width_strategy: WidthStrategy = WidthStrategy.CENTER
    height_strategy: HeightStrategy = HeightStrategy.CENTER


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

                img = ImageConverter.convert_color_space(
                    img, task.conversion_settings.color_space
                )

                if stitch_enabled:
                    stitch_images.append(img)
                else:
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
                stitched = ImageStitcher.stitch(
                    stitch_images,
                    direction=task.export_settings.stitch_settings.direction,
                    gap=task.export_settings.stitch_settings.gap,
                    bg_color=task.export_settings.stitch_settings.bg_color,
                    width_strategy=task.export_settings.stitch_settings.width_strategy,
                    height_strategy=task.export_settings.stitch_settings.height_strategy
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
                    f"{file_name}_长图.{fmt_ext}",
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
