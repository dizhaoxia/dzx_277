import fitz
import os
from dataclasses import dataclass
from typing import Optional, Tuple, List
from PIL import Image
import io


@dataclass
class PdfMetadata:
    file_path: str
    file_name: str
    total_pages: int
    page_width_pt: float
    page_height_pt: float
    is_encrypted: bool
    pdf_version: str
    is_valid: bool = True
    error_message: str = ""

    @property
    def page_size_mm(self) -> Tuple[float, float]:
        mm_per_pt = 25.4 / 72
        return (self.page_width_pt * mm_per_pt, self.page_height_pt * mm_per_pt)

    @property
    def page_size_inch(self) -> Tuple[float, float]:
        return (self.page_width_pt / 72, self.page_height_pt / 72)


class PdfParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._doc: Optional[fitz.Document] = None
        self._metadata: Optional[PdfMetadata] = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self, password: str = "") -> bool:
        try:
            self._doc = fitz.open(self.file_path)
            if self._doc.is_encrypted:
                if password:
                    result = self._doc.authenticate(password)
                    if result == 0:
                        return False
                else:
                    return False
            self._extract_metadata()
            return True
        except Exception as e:
            self._metadata = PdfMetadata(
                file_path=self.file_path,
                file_name=os.path.basename(self.file_path),
                total_pages=0,
                page_width_pt=0,
                page_height_pt=0,
                is_encrypted=False,
                pdf_version="",
                is_valid=False,
                error_message=str(e)
            )
            return False

    def close(self):
        if self._doc:
            self._doc.close()
            self._doc = None

    @property
    def is_encrypted(self) -> bool:
        if self._doc:
            return self._doc.is_encrypted
        return False

    def authenticate(self, password: str) -> bool:
        if self._doc and self._doc.is_encrypted:
            result = self._doc.authenticate(password)
            if result > 0:
                self._extract_metadata()
                return True
        return False

    def _extract_metadata(self):
        if not self._doc:
            return

        file_name = os.path.basename(self.file_path)
        total_pages = len(self._doc)

        first_page = self._doc[0] if total_pages > 0 else None
        page_width_pt = first_page.rect.width if first_page else 0
        page_height_pt = first_page.rect.height if first_page else 0

        is_encrypted = self._doc.is_encrypted

        pdf_version = ""
        metadata = self._doc.metadata
        if metadata:
            pdf_version = metadata.get("format", "")
            if pdf_version:
                pdf_version = pdf_version.replace("PDF ", "")

        self._metadata = PdfMetadata(
            file_path=self.file_path,
            file_name=file_name,
            total_pages=total_pages,
            page_width_pt=page_width_pt,
            page_height_pt=page_height_pt,
            is_encrypted=is_encrypted,
            pdf_version=pdf_version
        )

    @property
    def metadata(self) -> Optional[PdfMetadata]:
        return self._metadata

    def get_page_image(self, page_num: int, dpi: int = 150, 
                       colorspace: str = "rgb") -> Optional[Image.Image]:
        if not self._doc or page_num < 0 or page_num >= len(self._doc):
            return None

        page = self._doc[page_num]
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        cs = fitz.csRGB
        if colorspace.lower() == "cmyk":
            cs = fitz.csCMYK
        elif colorspace.lower() == "gray":
            cs = fitz.csGRAY

        pix = page.get_pixmap(matrix=matrix, colorspace=cs, alpha=True)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        return img

    def get_page_pixmap(self, page_num: int, dpi: int = 150):
        if not self._doc or page_num < 0 or page_num >= len(self._doc):
            return None
        page = self._doc[page_num]
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        return page.get_pixmap(matrix=matrix, alpha=True)

    @property
    def page_count(self) -> int:
        if self._doc:
            return len(self._doc)
        return 0

    def get_page_size_pt(self, page_num: int = 0) -> Tuple[float, float]:
        if not self._doc or page_num < 0 or page_num >= len(self._doc):
            return (0, 0)
        page = self._doc[page_num]
        return (page.rect.width, page.rect.height)


def check_encrypted(file_path: str) -> bool:
    try:
        doc = fitz.open(file_path)
        encrypted = doc.is_encrypted
        doc.close()
        return encrypted
    except Exception:
        return False


def get_pdf_info(file_path: str) -> Optional[PdfMetadata]:
    try:
        parser = PdfParser(file_path)
        parser.open()
        metadata = parser.metadata
        parser.close()
        return metadata
    except Exception:
        return None
