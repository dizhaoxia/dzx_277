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

        converted_images = ImageStitcher._normalize_alpha(images, bg_color)

        if len(converted_images) == 1:
            if bg_color == BackgroundColor.TRANSPARENT:
                return converted_images[0].copy()
            else:
                img = converted_images[0]
                mode = "RGBA" if bg_color == BackgroundColor.TRANSPARENT else "RGB"
                bg_tuple = bg_color.get_rgba() if mode == "RGBA" else bg_color.get_rgb()
                result = Image.new(mode, img.size, bg_tuple)
                result.paste(img, (0, 0))
                return result

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
        target_rgb = bg_color.get_rgb()
        target_rgba = bg_color.get_rgba()

        for img in images:
            if bg_color == BackgroundColor.TRANSPARENT:
                if img.mode != "RGBA":
                    if "A" in img.mode:
                        img = img.convert("RGBA")
                    else:
                        new_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
                        if img.mode == "RGB":
                            new_img.paste(img, (0, 0))
                        else:
                            new_img.paste(img.convert("RGBA"), (0, 0))
                        img = new_img
                result.append(img)
            else:
                if img.mode in ("RGBA", "LA", "PA"):
                    bg = Image.new("RGB", img.size, target_rgb)
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

    @staticmethod
    def create_grid(images: List[Image.Image],
                    columns: int = 3,
                    gap: int = 10,
                    bg_color: BackgroundColor = BackgroundColor.WHITE,
                    cell_width: int = 0) -> Image.Image:
        if not images:
            raise ValueError("No images to create grid")

        if columns < 1:
            columns = 1

        converted_images = ImageStitcher._normalize_alpha(images, bg_color)

        if cell_width and cell_width > 0:
            resized = []
            for img in converted_images:
                ratio = cell_width / img.width
                new_height = max(1, int(img.height * ratio))
                resized.append(img.resize((cell_width, new_height), Image.LANCZOS))
            converted_images = resized

        num_images = len(converted_images)
        num_rows = (num_images + columns - 1) // columns

        col_widths = [0] * columns
        row_heights = [0] * num_rows

        for idx, img in enumerate(converted_images):
            col = idx % columns
            row = idx // columns
            if img.width > col_widths[col]:
                col_widths[col] = img.width
            if img.height > row_heights[row]:
                row_heights[row] = img.height

        total_width = sum(col_widths) + gap * (columns - 1)
        total_height = sum(row_heights) + gap * (num_rows - 1)

        has_alpha = bg_color == BackgroundColor.TRANSPARENT
        if has_alpha:
            mode = "RGBA"
            bg_tuple = bg_color.get_rgba()
        else:
            mode = "RGB"
            bg_tuple = bg_color.get_rgb()

        result = Image.new(mode, (total_width, total_height), bg_tuple)

        y_offsets = [0] * num_rows
        cumulative = 0
        for r in range(num_rows):
            y_offsets[r] = cumulative
            cumulative += row_heights[r] + gap

        x_offsets = [0] * columns
        cumulative = 0
        for c in range(columns):
            x_offsets[c] = cumulative
            cumulative += col_widths[c] + gap

        for idx, img in enumerate(converted_images):
            col = idx % columns
            row = idx // columns
            x = x_offsets[col] + (col_widths[col] - img.width) // 2
            y = y_offsets[row] + (row_heights[row] - img.height) // 2
            result.paste(img, (x, y))

        return result
