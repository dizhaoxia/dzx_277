from PIL import Image
from typing import List, Tuple
from enum import Enum


class StitchDirection(Enum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


class WidthStrategy(Enum):
    STRETCH = "stretch"
    CENTER = "center"


class HeightStrategy(Enum):
    STRETCH = "stretch"
    CENTER = "center"


class BackgroundColor(Enum):
    WHITE = "white"
    BLACK = "black"
    TRANSPARENT = "transparent"

    def get_rgba(self) -> Tuple[int, int, int, int]:
        if self == BackgroundColor.WHITE:
            return (255, 255, 255, 255)
        elif self == BackgroundColor.BLACK:
            return (0, 0, 0, 255)
        else:
            return (0, 0, 0, 0)

    def get_rgb(self) -> Tuple[int, int, int]:
        if self == BackgroundColor.WHITE:
            return (255, 255, 255)
        elif self == BackgroundColor.BLACK:
            return (0, 0, 0)
        else:
            return (0, 0, 0)


class ImageStitcher:
    @staticmethod
    def stitch(images: List[Image.Image],
               direction: StitchDirection = StitchDirection.VERTICAL,
               gap: int = 0,
               bg_color: BackgroundColor = BackgroundColor.WHITE,
               width_strategy: WidthStrategy = WidthStrategy.CENTER,
               height_strategy: HeightStrategy = HeightStrategy.CENTER) -> Image.Image:
        if not images:
            raise ValueError("No images to stitch")

        if len(images) == 1:
            return images[0].copy()

        converted_images = ImageStitcher._normalize_alpha(images, bg_color)

        if direction == StitchDirection.VERTICAL:
            return ImageStitcher._stitch_vertical(
                converted_images, gap, bg_color, width_strategy
            )
        else:
            return ImageStitcher._stitch_horizontal(
                converted_images, gap, bg_color, height_strategy
            )

    @staticmethod
    def _normalize_alpha(images: List[Image.Image], 
                         bg_color: BackgroundColor) -> List[Image.Image]:
        result = []
        for img in images:
            if bg_color == BackgroundColor.TRANSPARENT:
                if img.mode != "RGBA":
                    if "A" in img.mode:
                        img = img.convert("RGBA")
                    else:
                        img = img.convert("RGBA")
                result.append(img)
            else:
                if img.mode in ("RGBA", "LA", "PA"):
                    bg = Image.new("RGB", img.size, bg_color.get_rgb())
                    if img.mode == "RGBA":
                        bg.paste(img, mask=img.split()[3])
                    elif img.mode == "LA":
                        bg.paste(img, mask=img.split()[1])
                    else:
                        bg.paste(img, mask=img.split()[-1])
                    result.append(bg)
                else:
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    result.append(img)
        return result

    @staticmethod
    def _stitch_vertical(images: List[Image.Image],
                         gap: int,
                         bg_color: BackgroundColor,
                         width_strategy: WidthStrategy) -> Image.Image:
        has_alpha = bg_color == BackgroundColor.TRANSPARENT

        max_width = max(img.width for img in images)
        total_height = sum(img.height for img in images) + gap * (len(images) - 1)

        if has_alpha:
            mode = "RGBA"
            bg_tuple = bg_color.get_rgba()
        else:
            mode = "RGB"
            bg_tuple = bg_color.get_rgb()

        result = Image.new(mode, (max_width, total_height), bg_tuple)

        y_offset = 0
        for img in images:
            if img.width != max_width:
                if width_strategy == WidthStrategy.STRETCH:
                    img = img.resize((max_width, img.height), Image.LANCZOS)
                    result.paste(img, (0, y_offset))
                else:
                    x_offset = (max_width - img.width) // 2
                    result.paste(img, (x_offset, y_offset))
            else:
                result.paste(img, (0, y_offset))

            y_offset += img.height + gap

        return result

    @staticmethod
    def _stitch_horizontal(images: List[Image.Image],
                           gap: int,
                           bg_color: BackgroundColor,
                           height_strategy: HeightStrategy) -> Image.Image:
        has_alpha = bg_color == BackgroundColor.TRANSPARENT

        max_height = max(img.height for img in images)
        total_width = sum(img.width for img in images) + gap * (len(images) - 1)

        if has_alpha:
            mode = "RGBA"
            bg_tuple = bg_color.get_rgba()
        else:
            mode = "RGB"
            bg_tuple = bg_color.get_rgb()

        result = Image.new(mode, (total_width, max_height), bg_tuple)

        x_offset = 0
        for img in images:
            if img.height != max_height:
                if height_strategy == HeightStrategy.STRETCH:
                    img = img.resize((img.width, max_height), Image.LANCZOS)
                    result.paste(img, (x_offset, 0))
                else:
                    y_offset = (max_height - img.height) // 2
                    result.paste(img, (x_offset, y_offset))
            else:
                result.paste(img, (x_offset, 0))

            x_offset += img.width + gap

        return result
