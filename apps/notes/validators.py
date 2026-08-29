import os
from django.core.exceptions import ValidationError

ALLOWED_NOTE_EXTENSIONS = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.png', '.jpg', '.jpeg']
MAX_NOTE_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


def validate_note_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_NOTE_EXTENSIONS:
        allowed_str = ', '.join(ALLOWED_NOTE_EXTENSIONS)
        raise ValidationError(f"Unsupported file format '{ext}'. Allowed formats: {allowed_str}")


def validate_note_file_size(value):
    if value.size > MAX_NOTE_FILE_SIZE:
        max_mb = MAX_NOTE_FILE_SIZE // (1024 * 1024)
        raise ValidationError(f"File size exceeds maximum allowed limit of {max_mb}MB.")
