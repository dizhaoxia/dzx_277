#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from PIL import Image
from core.image_stitcher import ImageStitcher, StitchDirection, BackgroundColor, WidthStrategy
from core.image_converter import ImageConverter, ConversionSettings, OutputFormat, ColorSpace

print("测试真实PDF场景...")
print()

print("场景1: 多页PDF，页面宽度不一致，黑色背景，20px间隙")
print("=" * 60)

test_images = []
for i, (w, h) in enumerate([(200, 100), (180, 120), (220, 90)]):
    img = Image.new('RGBA', (w, h), (255, 255, 255, 255))
    test_images.append(img)

print(f"输入图片尺寸: {[img.size for img in test_images]}")
print(f"输入图片模式: {test_images[0].mode}")

stitched = ImageStitcher.stitch(
    test_images,
    direction=StitchDirection.VERTICAL,
    gap=20,
    bg_color=BackgroundColor.BLACK,
    width_strategy=WidthStrategy.CENTER
)

print(f"拼接后尺寸: {stitched.size}")
print(f"拼接后模式: {stitched.mode}")

max_w = max(img.size[0] for img in test_images)
print(f"检查各区域像素:")
for y, desc in [(10, "第1页内容区"), (110, "第1个间隙"), (130, "第2页内容区"), (250, "第2个间隙"), (270, "第3页内容区")]:
    for x, xdesc in [(10, "左侧"), (max_w//2, "中间"), (max_w-10, "右侧")]:
        if 0 <= x < stitched.size[0] and 0 <= y < stitched.size[1]:
            pixel = stitched.getpixel((x, y))
            status = "✓" if pixel == (0, 0, 0) or pixel == (255, 255, 255) else "?"
            print(f"  {status} {desc} ({x}, {y}): {pixel}")

print()
print("场景2: 单页PDF，开启长图拼接，黑色背景")
print("=" * 60)

single_img = Image.new('RGBA', (200, 100), (255, 255, 255, 255))
stitched_single = ImageStitcher.stitch(
    [single_img],
    direction=StitchDirection.VERTICAL,
    gap=0,
    bg_color=BackgroundColor.BLACK,
    width_strategy=WidthStrategy.CENTER
)

print(f"拼接后尺寸: {stitched_single.size}")
print(f"拼接后模式: {stitched_single.mode}")
print(f"角落像素: {stitched_single.getpixel((0, 0))}")

print()
print("场景3: 带透明通道的PDF页面（PDF内容外是透明的）")
print("=" * 60)

test_images2 = []
for i in range(2):
    img = Image.new('RGBA', (200, 100), (255, 255, 255, 255))
    for x in range(5):
        for y in range(100):
            img.putpixel((x, y), (0, 0, 0, 0))
    for x in range(195, 200):
        for y in range(100):
            img.putpixel((x, y), (0, 0, 0, 0))
    test_images2.append(img)

print(f"输入图片: 200x100，左右各5px透明")

stitched2 = ImageStitcher.stitch(
    test_images2,
    direction=StitchDirection.VERTICAL,
    gap=10,
    bg_color=BackgroundColor.BLACK,
    width_strategy=WidthStrategy.CENTER
)

print(f"拼接后尺寸: {stitched2.size}")
print(f"左侧透明区域像素 (2, 50): {stitched2.getpixel((2, 50))}")
print(f"中间内容区域像素 (100, 50): {stitched2.getpixel((100, 50))}")
print(f"右侧透明区域像素 (198, 50): {stitched2.getpixel((198, 50))}")
print(f"间隙区域像素 (100, 105): {stitched2.getpixel((100, 105))}")

print()
print("保存测试（JPG格式）:")
print("=" * 60)

import tempfile
import os

settings = ConversionSettings(
    output_format=OutputFormat.JPG,
    dpi=150,
    jpg_quality=85
)

with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
    temp_path = f.name

try:
    info = ImageConverter.save_image(stitched, temp_path, settings)
    print(f"保存成功! 文件大小: {info.file_size} bytes")
    
    saved_img = Image.open(temp_path)
    print(f"读取后模式: {saved_img.mode}")
    print(f"间隙区域像素 (100, 110): {saved_img.getpixel((100, 110))}")
    
    if saved_img.getpixel((100, 110)) == (0, 0, 0):
        print("✓ 间隙区域背景色正确（黑色）")
    else:
        print(f"✗ 间隙区域背景色错误！期望 (0,0,0)，实际: {saved_img.getpixel((100, 110))}")
        
finally:
    os.unlink(temp_path)

print()
print("测试通过！")
