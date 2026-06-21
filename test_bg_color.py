#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from PIL import Image
from core.image_stitcher import ImageStitcher, StitchDirection, BackgroundColor, WidthStrategy
from core.image_converter import ImageConverter, ConversionSettings, OutputFormat

print("测试背景色功能...")
print()

test_images = []
for i in range(3):
    img = Image.new('RGBA', (200, 100), (255, 255, 255, 255))
    test_images.append(img)

print(f"测试图片: {len(test_images)} 张，每张 200x100")
print()

for bg_name, bg_color in [("WHITE", BackgroundColor.WHITE), ("BLACK", BackgroundColor.BLACK)]:
    print(f"测试背景色: {bg_name}")
    print(f"  get_rgb(): {bg_color.get_rgb()}")
    print(f"  get_rgba(): {bg_color.get_rgba()}")
    
    try:
        stitched = ImageStitcher.stitch(
            test_images,
            direction=StitchDirection.VERTICAL,
            gap=20,
            bg_color=bg_color,
            width_strategy=WidthStrategy.CENTER
        )
        
        print(f"  拼接后尺寸: {stitched.size}")
        print(f"  拼接后模式: {stitched.mode}")
        
        if hasattr(stitched, 'getpixel'):
            mid_y = 100 + 10
            pixel = stitched.getpixel((100, mid_y))
            print(f"  间隙区域像素 (100, {mid_y}): {pixel}")
            
            if bg_color == BackgroundColor.BLACK:
                if pixel == (0, 0, 0) or pixel == (0, 0, 0, 255):
                    print("  ✓ 背景色正确（黑色）")
                else:
                    print(f"  ✗ 背景色错误！期望黑色，实际: {pixel}")
            else:
                if pixel == (255, 255, 255) or pixel == (255, 255, 255, 255):
                    print("  ✓ 背景色正确（白色）")
                else:
                    print(f"  ✗ 背景色错误！期望白色，实际: {pixel}")
        
        print()
        
    except Exception as e:
        print(f"  ✗ 拼接失败: {e}")
        import traceback
        traceback.print_exc()
        print()

print("测试保存功能...")
settings = ConversionSettings(
    output_format=OutputFormat.JPG,
    dpi=150,
    jpg_quality=85
)

stitched_black = ImageStitcher.stitch(
    test_images,
    direction=StitchDirection.VERTICAL,
    gap=20,
    bg_color=BackgroundColor.BLACK,
    width_strategy=WidthStrategy.CENTER
)

print(f"保存前模式: {stitched_black.mode}")
print(f"保存前尺寸: {stitched_black.size}")

import tempfile
import os
with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
    temp_path = f.name

try:
    info = ImageConverter.save_image(stitched_black, temp_path, settings)
    print(f"保存成功! 文件大小: {info.file_size} bytes")
    
    saved_img = Image.open(temp_path)
    print(f"读取后模式: {saved_img.mode}")
    mid_y = 100 + 10
    pixel = saved_img.getpixel((100, mid_y))
    print(f"保存后间隙区域像素: {pixel}")
    
    if pixel == (0, 0, 0):
        print("✓ 保存后背景色仍正确（黑色）")
    else:
        print(f"✗ 保存后背景色错误！实际: {pixel}")
        
finally:
    os.unlink(temp_path)
