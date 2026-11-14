import os
import re
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

from app.core.config import settings


class FileValidationError(Exception):
    """Base exception for file validation and security failures."""
    pass


class InvalidFileSignatureError(FileValidationError):
    """Raised when file magic bytes do not match expected format."""
    pass


class FileSizeLimitExceededError(FileValidationError):
    """Raised when file size exceeds system threshold."""
    pass


class UnsupportedFileTypeError(FileValidationError):
    """Raised when an unapproved file extension or MIME type is uploaded."""
    pass


class PathTraversalSecurityError(FileValidationError):
    """Raised when filename attempts path traversal or directory manipulation."""
    pass


# Magic bytes (file signatures)
MAGIC_SIGNATURES = {
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
    "webp": [b"RIFF"],  # also checks bytes 8..12 == b"WEBP"
    "pdf": [b"%PDF-"],
}

MIME_TO_FORMAT = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/pjpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/webp": "webp",
    "application/pdf": "pdf",
}

EXTENSION_TO_FORMAT = {
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".webp": "webp",
    ".pdf": "pdf",
}


class FileValidator:
    """
    Validates file integrity, magic bytes, MIME types, and sanitizes filenames
    to prevent file upload exploits, path traversal, and malicious execution.
    """

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        r"""
        Sanitizes filename:
        - Rejects path traversal indicators (../, ..\)
        - Strips directory components
        - Replaces unsafe characters with underscores
        """
        if not filename or not filename.strip():
            return "unnamed_upload"

        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            # Strip path and keep only basename
            cleaned = os.path.basename(filename.replace("\\", "/"))
            if not cleaned or ".." in cleaned:
                raise PathTraversalSecurityError(
                    f"Malicious filename detected: '{filename}'. Path traversal is strictly forbidden."
                )
            filename = cleaned

        # Keep alphanumeric, dot, underscore, and dash only
        base, ext = os.path.splitext(filename)
        sanitized_base = re.sub(r"[^\w\-_]", "_", base)
        sanitized_ext = ext.lower()
        
        final_name = f"{sanitized_base}{sanitized_ext}"
        return final_name[:200]

    @classmethod
    def detect_format_from_bytes(cls, content: bytes) -> Optional[str]:
        """Inspects binary header (magic bytes) to determine actual file format."""
        if not content:
            return None

        # PNG
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"

        # JPEG
        if content.startswith(b"\xff\xd8\xff"):
            return "jpeg"

        # WebP: RIFF????WEBP
        if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            return "webp"

        # PDF
        if content.startswith(b"%PDF-"):
            return "pdf"

        return None

    @classmethod
    def validate_image_upload(
        cls,
        content: bytes,
        filename: str,
        declared_mime: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Validates an educational image upload:
        1. Non-empty check
        2. Size limit check (max 10MB)
        3. Sanitizes filename
        4. Matches file extension with approved formats (png, jpg, jpeg, webp)
        5. Validates binary magic bytes match extension & MIME type
        
        Returns:
            Tuple[detected_format, sanitized_filename]
        """
        if not content or len(content) == 0:
            raise FileValidationError(f"File '{filename}' is empty (0 bytes).")

        if len(content) > settings.MAX_IMAGE_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_IMAGE_UPLOAD_SIZE_BYTES / (1024 * 1024)
            actual_mb = len(content) / (1024 * 1024)
            raise FileSizeLimitExceededError(
                f"Image size ({actual_mb:.2f} MB) exceeds maximum allowed limit of {max_mb:.1f} MB."
            )

        safe_filename = cls.sanitize_filename(filename)
        ext = os.path.splitext(safe_filename)[1].lower()

        if ext not in EXTENSION_TO_FORMAT or ext == ".pdf":
            raise UnsupportedFileTypeError(
                f"Unsupported image format '{ext}'. Supported formats: .png, .jpg, .jpeg, .webp"
            )

        expected_format = EXTENSION_TO_FORMAT[ext]
        detected_format = cls.detect_format_from_bytes(content)

        if not detected_format or detected_format != expected_format:
            raise InvalidFileSignatureError(
                f"File signature mismatch: File '{safe_filename}' claims to be '{ext}' "
                f"but binary magic bytes indicate '{detected_format or 'unknown/corrupt'}'. "
                f"Upload rejected for security."
            )

        # Validate against declared MIME if provided
        if declared_mime:
            norm_mime = declared_mime.lower().split(";")[0].strip()
            if norm_mime in MIME_TO_FORMAT:
                mime_format = MIME_TO_FORMAT[norm_mime]
                if mime_format != detected_format:
                    raise InvalidFileSignatureError(
                        f"MIME type mismatch: Content-Type '{declared_mime}' disagrees with "
                        f"actual image binary signature '{detected_format}'."
                    )

        return detected_format, safe_filename

    @classmethod
    def get_user_storage_path(
        cls,
        user_id: UUID,
        file_id: UUID,
        subfolder: str = "images",
        extension: str = "png",
    ) -> Path:
        """
        Creates and returns a secure user-partitioned storage path.
        Directory structure: ./data/uploads/{user_id}/{subfolder}/{file_id}.{extension}
        """
        base_dir = Path(settings.UPLOAD_DIR).resolve()
        user_dir = base_dir / str(user_id) / subfolder
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / f"{file_id}.{extension.lstrip('.')}"
