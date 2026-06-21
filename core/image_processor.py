from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
import os


class FilterType(Enum):
    SHARPEN = "sharpen"
    CONTRAST_STRETCH = "contrast_stretch"
    DENOISE = "denoise"


class WatermarkType(Enum):
    TEXT = "text"
    IMAGE = "image"


class WatermarkPosition(Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"
    TILED = "tiled"


class CropMode(Enum):
    AUTO = "auto"
    DISABLED = "disabled"


@dataclass
class FilterConfig:
    filter_type: FilterType
    enabled: bool = True
    intensity: float = 1.0

    def to_dict(self) -> dict:
        return {
            "type": self.filter_type.value,
            "enabled": self.enabled,
            "intensity": self.intensity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FilterConfig":
        return cls(
            filter_type=FilterType(data["type"]),
            enabled=data.get("enabled", True),
            intensity=data.get("intensity", 1.0),
        )


@dataclass
class FilterChain:
    filters: List[FilterConfig] = field(default_factory=lambda: [
        FilterConfig(FilterType.CONTRAST_STRETCH, enabled=False, intensity=1.0),
        FilterConfig(FilterType.SHARPEN, enabled=False, intensity=1.0),
        FilterConfig(FilterType.DENOISE, enabled=False, intensity=1.0),
    ])

    def get_enabled_filters(self) -> List[FilterConfig]:
        return [f for f in self.filters if f.enabled]

    def to_list(self) -> List[dict]:
        return [f.to_dict() for f in self.filters]

    @classmethod
    def from_list(cls, data: List[dict]) -> "FilterChain":
        filters = [FilterConfig.from_dict(d) for d in data]
        return cls(filters=filters)

    def move_filter(self, from_idx: int, to_idx: int):
        if 0 <= from_idx < len(self.filters) and 0 <= to_idx < len(self.filters):
            filter_item = self.filters.pop(from_idx)
            self.filters.insert(to_idx, filter_item)


@dataclass
class TextWatermarkConfig:
    text: str = "水印文字"
    font_size: int = 36
    font_family: str = "Arial"
    color: Tuple[int, int, int, int] = (0, 0, 0, 128)
    opacity: int = 128
    rotation: float = 0.0
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    margin: int = 20
    tile_spacing_x: int = 200
    tile_spacing_y: int = 150


@dataclass
class ImageWatermarkConfig:
    image_path: str = ""
    opacity: float = 0.5
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    margin: int = 20
    scale: float = 1.0
    tile_spacing_x: int = 200
    tile_spacing_y: int = 150


@dataclass
class WatermarkSettings:
    enabled: bool = False
    type: WatermarkType = WatermarkType.TEXT
    text_config: TextWatermarkConfig = field(default_factory=TextWatermarkConfig)
    image_config: ImageWatermarkConfig = field(default_factory=ImageWatermarkConfig)

    def get_active_config(self):
        if self.type == WatermarkType.TEXT:
            return self.text_config
        return self.image_config


@dataclass
class CropSettings:
    enabled: bool = False
    mode: CropMode = CropMode.DISABLED
    threshold: int = 240
    padding: int = 0


class ImageProcessor:
    @staticmethod
    def apply_filter_chain(img: Image.Image, filter_chain: FilterChain) -> Image.Image:
        result = img.copy()
        for filter_cfg in filter_chain.get_enabled_filters():
            result = ImageProcessor._apply_single_filter(result, filter_cfg)
        return result

    @staticmethod
    def _apply_single_filter(img: Image.Image, cfg: FilterConfig) -> Image.Image:
        if cfg.filter_type == FilterType.SHARPEN:
            return ImageProcessor._apply_sharpen(img, cfg.intensity)
        elif cfg.filter_type == FilterType.CONTRAST_STRETCH:
            return ImageProcessor._apply_contrast_stretch(img)
        elif cfg.filter_type == FilterType.DENOISE:
            return ImageProcessor._apply_denoise(img, cfg.intensity)
        return img

    @staticmethod
    def _apply_sharpen(img: Image.Image, intensity: float) -> Image.Image:
        if img.mode not in ("RGB", "RGBA", "L", "LA"):
            img = img.convert("RGB")

        sharpener = ImageEnhance.Sharpness(img)
        factor = 1.0 + intensity * 2.0
        return sharpener.enhance(factor)

    @staticmethod
    def _apply_contrast_stretch(img: Image.Image) -> Image.Image:
        if img.mode in ("RGBA", "LA", "PA"):
            alpha = img.split()[-1]
            rgb_img = img.convert("RGB")
            stretched = ImageProcessor._stretch_rgb(rgb_img)
            if img.mode == "RGBA":
                r, g, b = stretched.split()
                return Image.merge("RGBA", (r, g, b, alpha))
            elif img.mode == "LA":
                l = stretched.convert("L")
                return Image.merge("LA", (l, alpha))
            else:
                return stretched
        elif img.mode == "RGB":
            return ImageProcessor._stretch_rgb(img)
        elif img.mode == "L":
            return ImageProcessor._stretch_grayscale(img)
        else:
            rgb_img = img.convert("RGB")
            return ImageProcessor._stretch_rgb(rgb_img)

    @staticmethod
    def _stretch_rgb(img: Image.Image) -> Image.Image:
        from PIL import ImageOps
        return ImageOps.autocontrast(img, cutoff=2)

    @staticmethod
    def _stretch_grayscale(img: Image.Image) -> Image.Image:
        from PIL import ImageOps
        return ImageOps.autocontrast(img, cutoff=2)

    @staticmethod
    def _apply_denoise(img: Image.Image, intensity: float) -> Image.Image:
        if img.mode in ("RGBA", "LA", "PA"):
            alpha = img.split()[-1]
            if img.mode == "RGBA":
                rgb_img = Image.merge("RGB", img.split()[:3])
            else:
                rgb_img = img.convert("RGB")
            radius = max(0.5, min(3.0, intensity * 2.0))
            denoised = rgb_img.filter(ImageFilter.GaussianBlur(radius=radius * 0.5))
            denoised = Image.blend(rgb_img, denoised, 0.3 + intensity * 0.2)
            if img.mode == "RGBA":
                r, g, b = denoised.split()
                return Image.merge("RGBA", (r, g, b, alpha))
            elif img.mode == "LA":
                l = denoised.convert("L")
                return Image.merge("LA", (l, alpha))
            else:
                return denoised
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")
            radius = max(0.5, min(3.0, intensity * 2.0))
            denoised = img.filter(ImageFilter.GaussianBlur(radius=radius * 0.5))
            return Image.blend(img, denoised, 0.3 + intensity * 0.2)

    @staticmethod
    def apply_watermark(img: Image.Image, settings: WatermarkSettings) -> Image.Image:
        if not settings.enabled:
            return img

        if settings.type == WatermarkType.TEXT:
            return ImageProcessor._apply_text_watermark(img, settings.text_config)
        else:
            return ImageProcessor._apply_image_watermark(img, settings.image_config)

    @staticmethod
    def _apply_text_watermark(img: Image.Image, cfg: TextWatermarkConfig) -> Image.Image:
        if img.mode != "RGBA":
            result = img.convert("RGBA")
        else:
            result = img.copy()

        try:
            font = ImageFont.truetype(cfg.font_family, cfg.font_size)
        except Exception:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

        if font is None:
            return img

        txt_layer = Image.new("RGBA", result.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_layer)

        text_bbox = draw.textbbox((0, 0), cfg.text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        color_with_opacity = (cfg.color[0], cfg.color[1], cfg.color[2], cfg.opacity)

        if cfg.rotation != 0:
            txt_img = Image.new("RGBA", (text_width + 20, text_height + 20), (0, 0, 0, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text((10, 10), cfg.text, font=font, fill=color_with_opacity)
            txt_img = txt_img.rotate(cfg.rotation, expand=True, resample=Image.BICUBIC)
            text_width = txt_img.width
            text_height = txt_img.height

            if cfg.position == WatermarkPosition.TILED:
                result = ImageProcessor._tile_watermark(result, txt_img, cfg.tile_spacing_x, cfg.tile_spacing_y)
            else:
                pos = ImageProcessor._get_watermark_position(
                    result.size, (text_width, text_height), cfg.position, cfg.margin
                )
                result.paste(txt_img, pos, txt_img)
        else:
            if cfg.position == WatermarkPosition.TILED:
                txt_img = Image.new("RGBA", (text_width + 10, text_height + 10), (0, 0, 0, 0))
                txt_draw = ImageDraw.Draw(txt_img)
                txt_draw.text((5, 5), cfg.text, font=font, fill=color_with_opacity)
                result = ImageProcessor._tile_watermark(result, txt_img, cfg.tile_spacing_x, cfg.tile_spacing_y)
            else:
                pos = ImageProcessor._get_watermark_position(
                    result.size, (text_width, text_height), cfg.position, cfg.margin
                )
                draw.text(pos, cfg.text, font=font, fill=color_with_opacity)
                result = Image.alpha_composite(result, txt_layer)

        if img.mode != "RGBA":
            result = result.convert(img.mode)

        return result

    @staticmethod
    def _apply_image_watermark(img: Image.Image, cfg: ImageWatermarkConfig) -> Image.Image:
        if not cfg.image_path or not os.path.exists(cfg.image_path):
            return img

        try:
            wm_img = Image.open(cfg.image_path).convert("RGBA")
        except Exception:
            return img

        if img.mode != "RGBA":
            result = img.convert("RGBA")
        else:
            result = img.copy()

        if cfg.scale != 1.0:
            new_w = int(wm_img.width * cfg.scale)
            new_h = int(wm_img.height * cfg.scale)
            if new_w > 0 and new_h > 0:
                wm_img = wm_img.resize((new_w, new_h), Image.LANCZOS)

        if cfg.opacity < 1.0:
            alpha = wm_img.split()[3]
            alpha = alpha.point(lambda p: int(p * cfg.opacity))
            wm_img.putalpha(alpha)

        if cfg.position == WatermarkPosition.TILED:
            result = ImageProcessor._tile_watermark(result, wm_img, cfg.tile_spacing_x, cfg.tile_spacing_y)
        else:
            pos = ImageProcessor._get_watermark_position(
                result.size, (wm_img.width, wm_img.height), cfg.position, cfg.margin
            )
            result.paste(wm_img, pos, wm_img)

        if img.mode != "RGBA":
            result = result.convert(img.mode)

        return result

    @staticmethod
    def _tile_watermark(base_img: Image.Image, wm_img: Image.Image, spacing_x: int, spacing_y: int) -> Image.Image:
        result = base_img.copy()
        wm_w, wm_h = wm_img.size
        base_w, base_h = result.size

        step_x = wm_w + spacing_x
        step_y = wm_h + spacing_y

        start_x = -wm_w // 2
        start_y = -wm_h // 2

        y = start_y
        while y < base_h:
            x = start_x
            while x < base_w:
                result.paste(wm_img, (x, y), wm_img)
                x += step_x
            y += step_y

        return result

    @staticmethod
    def _get_watermark_position(
        img_size: Tuple[int, int],
        wm_size: Tuple[int, int],
        position: WatermarkPosition,
        margin: int
    ) -> Tuple[int, int]:
        img_w, img_h = img_size
        wm_w, wm_h = wm_size

        if position == WatermarkPosition.TOP_LEFT:
            return (margin, margin)
        elif position == WatermarkPosition.TOP_RIGHT:
            return (img_w - wm_w - margin, margin)
        elif position == WatermarkPosition.BOTTOM_LEFT:
            return (margin, img_h - wm_h - margin)
        elif position == WatermarkPosition.BOTTOM_RIGHT:
            return (img_w - wm_w - margin, img_h - wm_h - margin)
        elif position == WatermarkPosition.CENTER:
            return ((img_w - wm_w) // 2, (img_h - wm_h) // 2)
        else:
            return (margin, img_h - wm_h - margin)

    @staticmethod
    def auto_crop_white_border(img: Image.Image, settings: CropSettings) -> Image.Image:
        if not settings.enabled or settings.mode == CropMode.DISABLED:
            return img

        threshold = settings.threshold
        padding = settings.padding

        if img.mode in ("RGBA", "LA", "PA"):
            alpha = img.split()[-1]
            rgb_img = img.convert("RGB")
            bbox = ImageProcessor._find_content_bbox(rgb_img, threshold)
            if bbox is None:
                return img
            left, top, right, bottom = bbox
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(rgb_img.width, right + padding)
            bottom = min(rgb_img.height, bottom + padding)
            cropped_rgb = rgb_img.crop((left, top, right, bottom))
            cropped_alpha = alpha.crop((left, top, right, bottom))
            if img.mode == "RGBA":
                r, g, b = cropped_rgb.split()
                return Image.merge("RGBA", (r, g, b, cropped_alpha))
            elif img.mode == "LA":
                l = cropped_rgb.convert("L")
                return Image.merge("LA", (l, cropped_alpha))
            else:
                return cropped_rgb
        else:
            if img.mode != "RGB":
                rgb_img = img.convert("RGB")
            else:
                rgb_img = img

            bbox = ImageProcessor._find_content_bbox(rgb_img, threshold)
            if bbox is None:
                return img

            left, top, right, bottom = bbox
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(rgb_img.width, right + padding)
            bottom = min(rgb_img.height, bottom + padding)

            if left >= right or top >= bottom:
                return img

            return img.crop((left, top, right, bottom))

    @staticmethod
    def _find_content_bbox(img: Image.Image, threshold: int) -> Optional[Tuple[int, int, int, int]]:
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        pixels = img.load()

        def is_white_pixel(x: int, y: int) -> bool:
            r, g, b = pixels[x, y]
            return r >= threshold and g >= threshold and b >= threshold

        left = 0
        found_left = False
        for x in range(w):
            for y in range(h):
                if not is_white_pixel(x, y):
                    left = x
                    found_left = True
                    break
            if found_left:
                break

        if not found_left:
            return None

        right = w - 1
        found_right = False
        for x in range(w - 1, -1, -1):
            for y in range(h):
                if not is_white_pixel(x, y):
                    right = x
                    found_right = True
                    break
            if found_right:
                break

        top = 0
        found_top = False
        for y in range(h):
            for x in range(w):
                if not is_white_pixel(x, y):
                    top = y
                    found_top = True
                    break
            if found_top:
                break

        bottom = h - 1
        found_bottom = False
        for y in range(h - 1, -1, -1):
            for x in range(w):
                if not is_white_pixel(x, y):
                    bottom = y
                    found_bottom = True
                    break
            if found_bottom:
                break

        if left >= right or top >= bottom:
            return None

        return (left, top, right + 1, bottom + 1)

    @staticmethod
    def process_full_pipeline(
        img: Image.Image,
        filter_chain: Optional[FilterChain] = None,
        crop_settings: Optional[CropSettings] = None,
        watermark_settings: Optional[WatermarkSettings] = None
    ) -> Image.Image:
        result = img

        if crop_settings and crop_settings.enabled:
            result = ImageProcessor.auto_crop_white_border(result, crop_settings)

        if filter_chain:
            result = ImageProcessor.apply_filter_chain(result, filter_chain)

        if watermark_settings and watermark_settings.enabled:
            result = ImageProcessor.apply_watermark(result, watermark_settings)

        return result
