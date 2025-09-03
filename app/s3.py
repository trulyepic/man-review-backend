import io
from urllib.parse import quote

import boto3
import uuid
import re
from app.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_BUCKET_NAME

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

def sanitize_folder_name(name: str) -> str:
    # Remove or replace any non-safe S3 characters
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

_SAFE_FILENAME_RE = re.compile(r'[^a-zA-Z0-9._-]+')

# def upload_to_s3(file_bytes, filename: str, content_type: str, folder: str) -> str:
#     sanitized_folder = sanitize_folder_name(folder)
#     unique_filename = f"{sanitized_folder}/covers/{uuid.uuid4()}_{filename}"
#     s3.upload_fileobj(
#         file_bytes,
#         AWS_BUCKET_NAME,
#         unique_filename,
#         ExtraArgs={"ContentType": content_type}
#     )
#     return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"

def upload_to_s3(file_bytes, filename: str, content_type: str, folder: str, *, subfolder: str = "covers") -> str:
    sanitized_folder = sanitize_folder_name(folder)
    sanitized_sub = sanitize_folder_name(subfolder)
    key = f"{sanitized_folder}/{sanitized_sub}/{uuid.uuid4()}_{filename}"
    s3.upload_fileobj(
        file_bytes,
        AWS_BUCKET_NAME,
        key,
        ExtraArgs={"ContentType": content_type}
    )

    key_encoded = quote(key, safe="/-._")
    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key_encoded}"

def delete_from_s3(key: str):
    s3.delete_object(Bucket=AWS_BUCKET_NAME, Key=key)


def sanitize_filename(name: str) -> str:
    """
    Make sure filenames are URL-safe and S3-friendly:
    - Trim whitespace
    - Replace spaces with '-'
    - Replace unsafe chars with '-'
    - Collapse repeats
    """
    name = name.strip()
    name = re.sub(r'\s+', '-', name)          # spaces -> dash
    name = _SAFE_FILENAME_RE.sub('-', name)   # unsafe -> dash
    name = re.sub(r'-{2,}', '-', name)        # collapse ---
    if not name:
        name = "file"
    return name

def upload_forum_media(file_bytes, filename: str, content_type: str, thread_id: int, user_id: int) -> str:
    """
    Specialized upload for forum memes/images/GIFs.
    Path: forum/<thread_id>/<user_id>/<uuid>_<filename>
    """
    sanitized_thread = sanitize_folder_name(str(thread_id))
    sanitized_user = sanitize_folder_name(str(user_id))
    safe_name = sanitize_filename(filename or "upload")

    key = f"forum/{sanitized_thread}/{sanitized_user}/{uuid.uuid4()}_{safe_name}"

    if isinstance(file_bytes, (bytes, bytearray)):
        file_bytes = io.BytesIO(file_bytes)

    s3.upload_fileobj(
        file_bytes,
        AWS_BUCKET_NAME,
        key,
        ExtraArgs={
            "ContentType": content_type,
            "ACL": "public-read",  # required for embedding in posts
            "CacheControl": "public, max-age=31536000, immutable",
        },
    )

    key_encoded = quote(key, safe="/-._")
    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key_encoded}"
