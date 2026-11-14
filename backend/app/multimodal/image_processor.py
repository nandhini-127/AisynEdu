import base64
import io
import logging
from dataclasses import dataclass
from typing import Optional, Tuple
from PIL import Image, ImageOps

logger = logging.getLogger("edunex.multimodal.image")


class ImageProcessingError(Exception):
    """Raised when image processing or decoding fails."""
    pass


class CorruptedImageError(ImageProcessingError):
    """Raised when image data cannot be decoded by PIL."""
    pass


@dataclass
class ImageMetadata:
    width: int
    height: int
    format: str
    mode: str
    aspect_ratio: float
    file_size_bytes: int


class ImageProcessor:
    """
    Image decoding, metadata extraction, validation, and thumbnail generation service.
    """

    MAX_DIMENSION = 4096  # Limit to 4K pixels in width or height to prevent decompression bombs

    @classmethod
    def load_and_inspect(cls, image_bytes: bytes) -> Tuple[Image.Image, ImageMetadata]:
        """
        Loads image bytes with PIL, verifies headers, and extracts dimensions.
        Raises CorruptedImageError if the image is invalid or unreadable.
        """
        if not image_bytes:
            raise CorruptedImageError("Empty image bytes provided.")

        try:
            stream = io.BytesIO(image_bytes)
            img = Image.open(stream)
            img.verify()  # Verifies file integrity
            
            # Reopen after verify() because verify() clears image state in PIL
            stream.seek(0)
            img = Image.open(stream)
            # Correct orientation if EXIF tag exists
            img = ImageOps.exif_transpose(img) or img
        except Exception as e:
            logger.error("Image decoding failed: %s", str(e))
            raise CorruptedImageError(f"Cannot decode image: {str(e)}") from e

        width, height = img.size
        if width > cls.MAX_DIMENSION or height > cls.MAX_DIMENSION:
            raise ImageProcessingError(
                f"Image dimensions ({width}x{height}) exceed maximum allowed dimension of {cls.MAX_DIMENSION}px."
            )

        meta = ImageMetadata(
            width=width,
            height=height,
            format=(img.format or "PNG").upper(),
            mode=img.mode,
            aspect_ratio=round(width / max(height, 1), 3),
            file_size_bytes=len(image_bytes),
        )

        return img, meta

    @classmethod
    def create_thumbnail_bytes(
        cls,
        image_bytes: bytes,
        max_size: Tuple[int, int] = (400, 400),
        output_format: str = "JPEG",
    ) -> bytes:
        """Generates a compressed thumbnail for fast preview and storage."""
        img, _ = cls.load_and_inspect(image_bytes)
        img_copy = img.copy()

        # Convert palette/transparency to RGB for JPEG
        if output_format.upper() == "JPEG" and img_copy.mode in ("RGBA", "P"):
            img_copy = img_copy.convert("RGB")

        img_copy.thumbnail(max_size, Image.Resampling.LANCZOS)
        out_stream = io.BytesIO()
        img_copy.save(out_stream, format=output_format, quality=85, optimize=True)
        return out_stream.getvalue()

    @classmethod
    def to_base64_data_uri(cls, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Converts image bytes to a base64 Data URI for HTML/web display."""
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{b64}"

    @classmethod
    def to_base64_raw(cls, image_bytes: bytes) -> str:
        """Converts raw image bytes to a base64 string."""
        return base64.b64encode(image_bytes).decode("utf-8")

