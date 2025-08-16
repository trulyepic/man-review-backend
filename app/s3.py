
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
    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"

def delete_from_s3(key: str):
    s3.delete_object(Bucket=AWS_BUCKET_NAME, Key=key)
