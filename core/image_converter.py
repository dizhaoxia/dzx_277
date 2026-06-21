from PIL import Image, ImageCms
import io
import os
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum


class OutputFormat(Enum):
    PNG = "png"
    JPG = "jpg"
    WEBP = "webp"


class ColorSpace(Enum):
    KEEP_ORIGINAL = "keep"
    FORCE_SRGB = "srgb"


@dataclass
class ConversionSettings:
    output_format: OutputFormat = OutputFormat.PNG
    dpi: int = 150
    color_space: ColorSpace = ColorSpace.KEEP_ORIGINAL
    jpg_quality: int = 85
    webp_quality: int = 80


@dataclass
class OutputInfo:
    width: int
    height: int
    dpi: int
    format: str
    file_size: int
    color_mode: str


class ImageConverter:
    SRGB_PROFILE = None
    CMYK_PROFILE = None

    @classmethod
    def _get_srgb_profile(cls):
        if cls.SRGB_PROFILE is None:
            try:
                cls.SRGB_PROFILE = ImageCms.createProfile("sRGB")
            except Exception:
                cls.SRGB_PROFILE = None
        return cls.SRGB_PROFILE

    @classmethod
    def convert_color_space(cls, img: Image.Image, target_space: ColorSpace) -> Image.Image:
        if target_space == ColorSpace.KEEP_ORIGINAL:
            return img

        if target_space == ColorSpace.FORCE_SRGB:
            if img.mode == "CMYK":
                try:
                    srgb_profile = cls._get_srgb_profile()
                    if srgb_profile:
                        img = ImageCms.profileToProfile(img, "CMYK", srgb_profile, outputMode="RGB")
                    else:
                        img = img.convert("RGB")
                except Exception:
                    img = img.convert("RGB")
            elif img.mode in ("RGBA", "LA", "PA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img, mask=img.split()[1])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

        return img

    @classmethod
    def prepare_for_format(cls, img: Image.Image, fmt: OutputFormat, 
                           quality: int = 85) -> Image.Image:
        if fmt == OutputFormat.PNG:
            if img.mode not in ("RGBA", "RGB", "P"):
                if "A" in img.mode:
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")
            return img

        elif fmt == OutputFormat.JPG:
            if img.mode in ("RGBA", "LA", "PA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[3])
                elif img.mode == "LA":
                    background.paste(img, mask=img.split()[1])
                else:
                    background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode == "CMYK":
                img = img.convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")
            return img

        elif fmt == OutputFormat.WEBP:
            if img.mode not in ("RGBA", "RGB"):
                if "A" in img.mode:
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")
            return img

        return img

    @classmethod
    def save_image(cls, img: Image.Image, output_path: str, 
                   settings: ConversionSettings) -> OutputInfo:
        fmt = settings.output_format
        img = cls.prepare_for_format(img, fmt, settings.jpg_quality)

        ext = fmt.value
        if not output_path.lower().endswith(f".{ext}"):
            output_path = f"{output_path}.{ext}"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        max_dimension = max(img.width, img.height)
        if max_dimension > 30000:
            import warnings
            warnings.warn(f"图片尺寸过大 ({img.width}x{img.height})，可能导致保存失败")

        save_kwargs = {}
        if fmt == OutputFormat.PNG:
            if max_dimension > 30000:
                save_kwargs["optimize"] = False
                save_kwargs["compress_level"] = 1
            else:
                save_kwargs["optimize"] = True
        elif fmt == OutputFormat.JPG:
            save_kwargs["quality"] = settings.jpg_quality
            if max_dimension > 65000:
                raise ValueError(
                    f"JPG 格式不支持超过 65535 像素的尺寸 "
                    f"(当前: {img.width}x{img.height})。"
                    f"请降低 DPI 或减少拼接页数，或使用 PNG/WebP 格式。"
                )
            elif max_dimension > 30000:
                save_kwargs["optimize"] = False
                save_kwargs["progressive"] = False
            else:
                save_kwargs["optimize"] = True
                save_kwargs["progressive"] = True
        elif fmt == OutputFormat.WEBP:
            save_kwargs["quality"] = settings.webp_quality
            if max_dimension > 16383:
                raise ValueError(
                    f"WebP 格式不支持超过 16383 像素的尺寸 "
                    f"(当前: {img.width}x{img.height})。"
                    f"请降低 DPI 或减少拼接页数，或使用 PNG 格式。"
                )
            elif max_dimension > 8000:
                save_kwargs["method"] = 3
            else:
                save_kwargs["method"] = 6

        try:
            img.save(output_path, **save_kwargs)
        except (IOError, OSError, ValueError) as e:
            if "broken data stream" in str(e).lower() or "image file" in str(e).lower():
                retry_kwargs = dict(save_kwargs)
                retry_kwargs.pop("optimize", None)
                retry_kwargs.pop("progressive", None)
                retry_kwargs.pop("method", None)
                retry_kwargs.pop("compress_level", None)
                if fmt == OutputFormat.JPG and "quality" not in retry_kwargs:
                    retry_kwargs["quality"] = settings.jpg_quality
                elif fmt == OutputFormat.WEBP and "quality" not in retry_kwargs:
                    retry_kwargs["quality"] = settings.webp_quality
                try:
                    img.save(output_path, **retry_kwargs)
                except Exception as e2:
                    raise RuntimeError(
                        f"图片保存失败（尺寸: {img.width}x{img.height}）。"
                        f"建议降低 DPI 或减少拼接页数。\n"
                        f"错误: {str(e2)}"
                    ) from e2
            else:
                raise

        file_size = os.path.getsize(output_path)

        return OutputInfo(
            width=img.width,
            height=img.height,
            dpi=settings.dpi,
            format=fmt.value.upper(),
            file_size=file_size,
            color_mode=img.mode
        )

    @classmethod
    def save_to_bytes(cls, img: Image.Image, settings: ConversionSettings) -> bytes:
        fmt = settings.output_format
        img = cls.prepare_for_format(img, fmt, settings.jpg_quality)

        buf = io.BytesIO()
        save_kwargs = {}
        if fmt == OutputFormat.PNG:
            save_kwargs["optimize"] = True
        elif fmt == OutputFormat.JPG:
            save_kwargs["quality"] = settings.jpg_quality
            save_kwargs["optimize"] = True
        elif fmt == OutputFormat.WEBP:
            save_kwargs["quality"] = settings.webp_quality
            save_kwargs["method"] = 6

        img.save(buf, format=fmt.value.upper(), **save_kwargs)
        return buf.getvalue()

    @classmethod
    def estimate_file_size(cls, width: int, height: int, 
                           settings: ConversionSettings) -> Tuple[int, int]:
        pixels = width * height

        if settings.output_format == OutputFormat.PNG:
            bytes_per_pixel = 0.5 if settings.color_space == ColorSpace.FORCE_SRGB else 0.6
            if width * height < 1000000:
                bytes_per_pixel *= 1.2
            estimated = int(pixels * bytes_per_pixel)
            return (int(estimated * 0.6), int(estimated * 1.4))

        elif settings.output_format == OutputFormat.JPG:
            quality_factor = settings.jpg_quality / 85.0
            base_bpp = 0.15 * quality_factor
            estimated = int(pixels * base_bpp)
            return (int(estimated * 0.7), int(estimated * 1.3))

        elif settings.output_format == OutputFormat.WEBP:
            quality_factor = settings.webp_quality / 80.0
            base_bpp = 0.1 * quality_factor
            estimated = int(pixels * base_bpp)
            return (int(estimated * 0.6), int(estimated * 1.4))

        return (0, 0)


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
