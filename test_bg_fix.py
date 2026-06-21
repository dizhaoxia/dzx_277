
"""测试背景色修复"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
from core.image_stitcher import (
    ImageStitcher, StitchDirection, BackgroundColor, WidthStrategy
)
from core.image_converter import (
    ImageConverter, ConversionSettings, OutputFormat, ColorSpace
)

def test_bg_color_after_color_space():
    """测试拼接后再进行色彩空间转换时背景色是否正确"""
    print("测试1：拼接背景色 + FORCE_SRGB 色彩空间转换")
    
    img1 = Image.new("RGBA", (200, 150), (255, 0, 0, 255))
    img2 = Image.new("RGBA", (180, 150), (0, 255, 0, 255))
    
    stitch_settings = {
        "direction": StitchDirection.VERTICAL,
        "gap": 20,
        "bg_color": BackgroundColor.BLACK,
        "width_strategy": WidthStrategy.CENTER,
    }
    
    stitched = ImageStitcher.stitch([img1, img2], **stitch_settings)
    print(f"  拼接后模式: {stitched.mode}")
    print(f"  拼接后尺寸: {stitched.size}")
    
    pixel = stitched.getpixel((0, 160))
    print(f"  间隙区域像素 (y=160): {pixel}")
    assert pixel == (0, 0, 0), f"间隙区域应该是黑色，实际是 {pixel}"
    
    conversion_settings = ConversionSettings(
        output_format=OutputFormat.JPG,
        dpi=150,
        color_space=ColorSpace.FORCE_SRGB,
        jpg_quality=85
    )
    
    converted = ImageConverter.convert_color_space(stitched, conversion_settings.color_space)
    print(f"  色彩空间转换后模式: {converted.mode}")
    
    pixel_after = converted.getpixel((0, 160))
    print(f"  转换后间隙区域像素 (y=160): {pixel_after}")
    assert pixel_after == (0, 0, 0), f"转换后间隙区域应该是黑色，实际是 {pixel_after}"
    
    print("  ✓ 通过")

def test_bg_color_with_transparent_bg():
    """测试透明背景 + FORCE_SRGB 时透明通道是否保留"""
    print("\n测试2：透明背景 + FORCE_SRGB 色彩空间转换")
    
    img1 = Image.new("RGBA", (200, 150), (255, 0, 0, 200))
    img2 = Image.new("RGBA", (200, 150), (0, 255, 0, 200))
    
    stitch_settings = {
        "direction": StitchDirection.VERTICAL,
        "gap": 10,
        "bg_color": BackgroundColor.TRANSPARENT,
        "width_strategy": WidthStrategy.CENTER,
    }
    
    stitched = ImageStitcher.stitch([img1, img2], **stitch_settings)
    print(f"  拼接后模式: {stitched.mode}")
    assert stitched.mode == "RGBA", f"透明背景应该保持 RGBA 模式"
    
    conversion_settings = ConversionSettings(
        output_format=OutputFormat.PNG,
        dpi=150,
        color_space=ColorSpace.FORCE_SRGB,
    )
    
    converted = ImageConverter.convert_color_space(stitched, conversion_settings.color_space)
    print(f"  色彩空间转换后模式: {converted.mode}")
    assert converted.mode == "RGBA", f"转换后应该保持 RGBA 模式"
    
    pixel = converted.getpixel((0, 155))
    print(f"  间隙区域像素 (y=155): {pixel}")
    assert pixel[3] == 0, f"透明区域 alpha 应该为 0"
    
    print("  ✓ 通过")

def test_single_page_with_color_space():
    """测试单页拼接 + FORCE_SRGB 时背景色是否正确"""
    print("\n测试3：单页拼接（带透明区域） + FORCE_SRGB")
    
    img = Image.new("RGBA", (200, 150), (255, 0, 0, 0))
    for x in range(50, 150):
        for y in range(30, 120):
            img.putpixel((x, y), (255, 0, 0, 255))
    
    stitch_settings = {
        "direction": StitchDirection.VERTICAL,
        "gap": 0,
        "bg_color": BackgroundColor.BLACK,
        "width_strategy": WidthStrategy.CENTER,
    }
    
    stitched = ImageStitcher.stitch([img], **stitch_settings)
    print(f"  拼接后模式: {stitched.mode}")
    print(f"  拼接后尺寸: {stitched.size}")
    
    conversion_settings = ConversionSettings(
        output_format=OutputFormat.JPG,
        dpi=150,
        color_space=ColorSpace.FORCE_SRGB,
    )
    
    converted = ImageConverter.convert_color_space(stitched, conversion_settings.color_space)
    
    prepared = ImageConverter.prepare_for_format(converted, conversion_settings.output_format)
    print(f"  格式准备后模式: {prepared.mode}")
    
    pixel_bg = prepared.getpixel((0, 0))
    print(f"  透明区域像素（背景填充）: {pixel_bg}")
    r, g, b = pixel_bg[:3]
    assert r < 30 and g < 30 and b < 30, f"透明区域应该填充黑色，实际是 {pixel_bg}"
    
    pixel_content = prepared.getpixel((100, 75))
    print(f"  内容区域像素: {pixel_content}")
    assert pixel_content[0] > 200, f"内容区域应该是红色"
    
    print("  ✓ 通过")

def test_save_image_with_bg_color():
    """测试完整流程：拼接 -> 色彩空间转换 -> 保存"""
    print("\n测试4：完整保存流程")
    
    import tempfile
    
    img1 = Image.new("RGBA", (200, 150), (255, 0, 0, 255))
    img2 = Image.new("RGBA", (180, 150), (0, 255, 0, 255))
    
    stitch_settings = {
        "direction": StitchDirection.VERTICAL,
        "gap": 20,
        "bg_color": BackgroundColor.BLACK,
        "width_strategy": WidthStrategy.CENTER,
    }
    
    stitched = ImageStitcher.stitch([img1, img2], **stitch_settings)
    
    conversion_settings = ConversionSettings(
        output_format=OutputFormat.JPG,
        dpi=150,
        color_space=ColorSpace.FORCE_SRGB,
        jpg_quality=90
    )
    
    stitched = ImageConverter.convert_color_space(stitched, conversion_settings.color_space)
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        temp_path = f.name
    
    try:
        info = ImageConverter.save_image(stitched, temp_path, conversion_settings)
        print(f"  保存成功: {info.width}x{info.height}, {info.color_mode}")
        
        saved_img = Image.open(temp_path)
        pixel = saved_img.getpixel((0, 160))
        print(f"  保存后间隙区域像素 (y=160): {pixel}")
        
        r, g, b = pixel[:3]
        assert r < 30 and g < 30 and b < 30, f"保存后间隙应该是黑色，实际是 {pixel}"
        
        print("  ✓ 通过")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    try:
        test_bg_color_after_color_space()
        test_bg_color_with_transparent_bg()
        test_single_page_with_color_space()
        test_save_image_with_bg_color()
        print("\n" + "="*50)
        print("所有测试通过！背景色问题已修复。")
        print("="*50)
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
