import os
import re
from datetime import datetime
from typing import List, Optional


class PageRangeParser:
    @staticmethod
    def parse(page_range_str: str, total_pages: int) -> List[int]:
        if not page_range_str or page_range_str.strip() == "":
            return list(range(1, total_pages + 1))

        pages = set()
        parts = page_range_str.split(",")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if "-" in part:
                match = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2))
                    if start > end:
                        start, end = end, start
                    start = max(1, min(start, total_pages))
                    end = max(1, min(end, total_pages))
                    for p in range(start, end + 1):
                        pages.add(p)
            else:
                try:
                    page = int(part)
                    if 1 <= page <= total_pages:
                        pages.add(page)
                except ValueError:
                    pass

        return sorted(list(pages))

    @staticmethod
    def validate(page_range_str: str) -> bool:
        if not page_range_str or page_range_str.strip() == "":
            return True

        parts = page_range_str.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if "-" in part:
                if not re.match(r"^\d+\s*-\s*\d+$", part):
                    return False
            else:
                if not re.match(r"^\d+$", part):
                    return False

        return True


class NamingTemplate:
    DEFAULT_TEMPLATE = "[原文件名]_第[页码]页"

    @staticmethod
    def get_available_placeholders() -> List[str]:
        return [
            "[原文件名]",
            "[页码]",
            "[总页数]",
            "[DPI]",
            "[日期]",
            "[格式]",
        ]

    @staticmethod
    def generate(template: str,
                 original_name: str,
                 page_num: int,
                 total_pages: int,
                 dpi: int,
                 fmt: str,
                 date_format: str = "%Y%m%d") -> str:
        result = template

        base_name = os.path.splitext(original_name)[0]

        page_num_str = str(page_num)
        total_pages_str = str(total_pages)
        pad_length = max(len(page_num_str), len(total_pages_str))
        if pad_length < 2:
            pad_length = 2

        result = result.replace("[原文件名]", base_name)
        result = result.replace("[页码]", str(page_num).zfill(pad_length))
        result = result.replace("[总页数]", str(total_pages))
        result = result.replace("[DPI]", str(dpi))
        result = result.replace("[格式]", fmt.lower())
        result = result.replace("[日期]", datetime.now().strftime(date_format))

        result = re.sub(r'[<>:"/\\|?*]', "_", result)

        return result


class OutputOrganizer:
    @staticmethod
    def get_output_path(output_dir: str,
                        file_name: str,
                        create_subfolder: bool,
                        original_file_name: str) -> str:
        if create_subfolder:
            subfolder_name = os.path.splitext(original_file_name)[0]
            subfolder_path = os.path.join(output_dir, subfolder_name)
            os.makedirs(subfolder_path, exist_ok=True)
            return os.path.join(subfolder_path, file_name)
        else:
            os.makedirs(output_dir, exist_ok=True)
            return os.path.join(output_dir, file_name)

    @staticmethod
    def get_unique_path(file_path: str) -> str:
        if not os.path.exists(file_path):
            return file_path

        base, ext = os.path.splitext(file_path)
        counter = 1
        while True:
            new_path = f"{base}_{counter}{ext}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1
