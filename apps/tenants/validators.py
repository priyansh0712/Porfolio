import os
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# Allowed extensions for school images and logos
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']

validate_image_extension = FileExtensionValidator(
    allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
    message=f"Only image files ({', '.join(ALLOWED_IMAGE_EXTENSIONS)}) are allowed."
)


def validate_image_file_size(file):
    """
    Validates that uploaded image file size does not exceed 5MB.
    """
    max_size_mb = 5
    max_size_bytes = max_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        raise ValidationError(f"File size must not exceed {max_size_mb}MB. Current file size: {file.size / (1024 * 1024):.1f}MB.")
