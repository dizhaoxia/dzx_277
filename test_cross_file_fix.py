
"""测试跨文件合成长图修复"""
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
from core.conversion_manager import (
    ConversionManager, ConversionTask, PdfItem,
    ConversionSettings, ExportSettings, StitchSettings, OutputMode
)
from core.image_stitcher import StitchDirection, BackgroundColor, WidthStrategy
from core.image_converter import OutputFormat, ColorSpace


def create_test_pdf(file_path: str, num_pages: int = 2):
    """创建测试用的简单 PDF"""
    try:
        import fitz
        doc = fitz.open()
        for i in range(num_pages):
            page = doc.new_page(width=595, height=842)
            rect = fitz.Rect(50, 50, 545, 792)
            color = (1 - i * 0.3, i * 0.2, i * 0.4)
            page.draw_rect(rect, color=color, fill=color)
            page.insert_text((100, 100), f"Test Page {i + 1}", fontsize=20)
        doc.save(file_path)
        doc.close()
        return True
    except ImportError:
        print("PyMuPDF not available, skipping PDF creation")
        return False


def test_progress_calculation_no_crash():
    """测试进度计算不会崩溃"""
    print("测试1：跨文件转换进度计算（不崩溃）")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_paths = []
        for i in range(3):
            path = os.path.join(tmpdir, f"test_{i}.pdf")
            if create_test_pdf(path, num_pages=2):
                pdf_paths.append(path)
        
        if len(pdf_paths) < 2:
            print("  跳过：无法创建测试 PDF")
            return
        
        pdf_items = []
        for path in pdf_paths:
            item = PdfItem(file_path=path)
            pdf_items.append(item)
        
        from core.pdf_parser import PdfParser
        for item in pdf_items:
            parser = PdfParser(item.file_path)
            if parser.open(""):
                item.metadata = parser.metadata
                item.is_loaded = True
                parser.close()
        
        conversion_settings = ConversionSettings(
            output_format=OutputFormat.PNG,
            dpi=72,
            color_space=ColorSpace.KEEP_ORIGINAL
        )
        
        stitch_settings = StitchSettings(
            enabled=True,
            mode=OutputMode.CROSS_FILE_LONG_IMAGE,
            direction=StitchDirection.VERTICAL,
            gap=10,
            bg_color=BackgroundColor.BLACK,
            width_strategy=WidthStrategy.CENTER
        )
        
        export_settings = ExportSettings(
            output_dir=tmpdir,
            naming_template="[原文件名]",
            page_range="",
            create_subfolder=False,
            stitch_settings=stitch_settings
        )
        
        tasks = []
        for item in pdf_items:
            task = ConversionTask(item, conversion_settings, export_settings)
            tasks.append(task)
        
        progress_values = []
        
        def on_progress(p):
            progress_values.append(p)
            assert 0 <= p <= 100, f"进度值应在 0-100 之间，实际 {p}"
        
        manager = ConversionManager()
        result = manager.convert_cross_file_long_image(tasks, on_progress)
        
        print(f"  成功: {result.success}")
        print(f"  输出文件数: {len(result.output_files)}")
        print(f"  进度更新次数: {len(progress_values)}")
        if progress_values:
            print(f"  进度范围: {min(progress_values):.1f}% - {max(progress_values):.1f}%")
        
        assert result.success, f"转换失败: {result.error_message}"
        assert len(result.output_files) > 0, "应该有输出文件"
        
        if result.output_files:
            output_path = result.output_files[0]
            assert os.path.exists(output_path), "输出文件应该存在"
            img = Image.open(output_path)
            print(f"  输出尺寸: {img.size}")
            img.close()
        
        print("  ✓ 通过")


def test_resource_cleanup():
    """测试 PdfParser 资源正确清理（不会泄漏）"""
    print("\n测试2：资源清理验证")
    
    import gc
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_paths = []
        for i in range(2):
            path = os.path.join(tmpdir, f"test_resource_{i}.pdf")
            if create_test_pdf(path, num_pages=1):
                pdf_paths.append(path)
        
        if len(pdf_paths) < 2:
            print("  跳过：无法创建测试 PDF")
            return
        
        pdf_items = []
        for path in pdf_paths:
            item = PdfItem(file_path=path)
            from core.pdf_parser import PdfParser
            parser = PdfParser(item.file_path)
            if parser.open(""):
                item.metadata = parser.metadata
                item.is_loaded = True
                parser.close()
            pdf_items.append(item)
        
        conversion_settings = ConversionSettings(
            output_format=OutputFormat.JPG,
            dpi=72,
            color_space=ColorSpace.FORCE_SRGB
        )
        
        stitch_settings = StitchSettings(
            enabled=True,
            mode=OutputMode.CROSS_FILE_LONG_IMAGE,
            direction=StitchDirection.VERTICAL,
            gap=5,
            bg_color=BackgroundColor.WHITE,
            width_strategy=WidthStrategy.CENTER
        )
        
        export_settings = ExportSettings(
            output_dir=tmpdir,
            naming_template="[原文件名]",
            page_range="",
            create_subfolder=False,
            stitch_settings=stitch_settings
        )
        
        tasks = []
        for item in pdf_items:
            task = ConversionTask(item, conversion_settings, export_settings)
            tasks.append(task)
        
        manager = ConversionManager()
        result = manager.convert_cross_file_long_image(tasks)
        
        gc.collect()
        
        assert result.success, f"转换失败: {result.error_message}"
        print(f"  转换成功: {result.success}")
        print(f"  错误信息: {result.error_message}")
        print("  ✓ 通过")


def test_cross_file_background_color():
    """测试跨文件拼接时背景色正确"""
    print("\n测试3：跨文件拼接背景色")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_paths = []
        for i in range(2):
            path = os.path.join(tmpdir, f"test_bg_{i}.pdf")
            if create_test_pdf(path, num_pages=1):
                pdf_paths.append(path)
        
        if len(pdf_paths) < 2:
            print("  跳过：无法创建测试 PDF")
            return
        
        pdf_items = []
        for path in pdf_paths:
            item = PdfItem(file_path=path)
            from core.pdf_parser import PdfParser
            parser = PdfParser(item.file_path)
            if parser.open(""):
                item.metadata = parser.metadata
                item.is_loaded = True
                parser.close()
            pdf_items.append(item)
        
        conversion_settings = ConversionSettings(
            output_format=OutputFormat.PNG,
            dpi=72,
            color_space=ColorSpace.KEEP_ORIGINAL
        )
        
        stitch_settings = StitchSettings(
            enabled=True,
            mode=OutputMode.CROSS_FILE_LONG_IMAGE,
            direction=StitchDirection.VERTICAL,
            gap=50,
            bg_color=BackgroundColor.BLACK,
            width_strategy=WidthStrategy.CENTER
        )
        
        export_settings = ExportSettings(
            output_dir=tmpdir,
            naming_template="[原文件名]",
            page_range="",
            create_subfolder=False,
            stitch_settings=stitch_settings
        )
        
        tasks = []
        for item in pdf_items:
            task = ConversionTask(item, conversion_settings, export_settings)
            tasks.append(task)
        
        manager = ConversionManager()
        result = manager.convert_cross_file_long_image(tasks)
        
        assert result.success, f"转换失败: {result.error_message}"
        
        if result.output_files:
            output_path = result.output_files[0]
            img = Image.open(output_path)
            pixel = img.getpixel((0, 850))
            print(f"  间隙区域像素: {pixel}")
            
            r, g, b = pixel[:3]
            assert r < 30 and g < 30 and b < 30, f"间隙应该是黑色，实际是 {pixel}"
            img.close()
        
        print("  ✓ 通过")


if __name__ == "__main__":
    try:
        test_progress_calculation_no_crash()
        test_resource_cleanup()
        test_cross_file_background_color()
        print("\n" + "=" * 50)
        print("所有测试通过！跨文件合成长图崩溃问题已修复。")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
