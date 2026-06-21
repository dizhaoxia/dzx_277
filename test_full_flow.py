#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from PIL import Image
from core.image_stitcher import ImageStitcher, StitchDirection, BackgroundColor, WidthStrategy
from core.image_converter import ImageConverter, ConversionSettings, OutputFormat, ColorSpace

print("模拟完整转换流程...")
print()

test_images = []
for i in range(3):
    img = Image.new('RGBA', (200, 100), (255, 255, 255, 255))
    test_images.append(img)

print(f"原始图片模式: {test_images[0].mode}")
print()

print("步骤1: 模拟色彩空间转换...")
settings = ConversionSettings(
    output_format=OutputFormat.JPG,
    dpi=150,
    color_space=ColorSpace.KEEP_ORIGINAL,
    jpg_quality=85
)

converted_images = []
for img in test_images:
    converted = ImageConverter.convert_color_space(img, settings.color_space)
    converted_images.append(converted)

print(f"转换后图片模式: {converted_images[0].mode}")
print()

print("步骤2: 拼接图片（黑色背景，20px间隙）...")
stitched = ImageStitcher.stitch(
    converted_images,
    direction=StitchDirection.VERTICAL,
    gap=20,
    bg_color=BackgroundColor.BLACK,
    width_strategy=WidthStrategy.CENTER
)

print(f"拼接后模式: {stitched.mode}")
print(f"拼接后尺寸: {stitched.size}")

mid_y = 100 + 10
pixel = stitched.getpixel((100, mid_y))
print(f"间隙区域像素: {pixel}")
print()

print("步骤3: 准备格式（JPG）...")
prepared = ImageConverter.prepare_for_format(stitched, settings.output_format, settings.jpg_quality)
print(f"准备后模式: {prepared.mode}")
print(f"准备后尺寸: {prepared.size}")

pixel = prepared.getpixel((100, mid_y))
print(f"准备后间隙区域像素: {pixel}")
print()

print("步骤4: 检查 save_image 流程...")
import tempfile
import os

with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
    temp_path = f.name

try:
    info = ImageConverter.save_image(stitched, temp_path, settings)
    print(f"保存成功! 文件大小: {info.file_size} bytes")
    
    saved_img = Image.open(temp_path)
    print(f"读取后模式: {saved_img.mode}")
    pixel = saved_img.getpixel((100, mid_y))
    print(f"保存后间隙区域像素: {pixel}")
    
    if pixel == (0, 0, 0):
        print("\n✓ 完整流程测试通过！背景色正确！")
    else:
        print(f"\n✗ 背景色错误！期望 (0,0,0)，实际: {pixel}")
        
finally:
    os.unlink(temp_path)

print()
print("测试 PNG 格式（支持透明）...")
settings_png = ConversionSettings(
    output_format=OutputFormat.PNG,
    dpi=150,
    color_space=ColorSpace.KEEP_ORIGINAL
)

with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    temp_path_png = f.name

try:
    info = ImageConverter.save_image(stitched, temp_path_png, settings_png)
    print(f"PNG 保存成功! 文件大小: {info.file_size} bytes")
    
    saved_img = Image.open(temp_path_png)
    print(f"PNG 读取后模式: {saved_img.mode}")
    pixel = saved_img.getpixel((100, mid_y))
    print(f"PNG 间隙区域像素: {pixel}")
    
finally:
    os.unlink(temp_path_png)
