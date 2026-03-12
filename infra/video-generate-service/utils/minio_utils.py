from minio import Minio

from celeryconfig import (MINIO_ACCESS_KEY, MINIO_HOST, MINIO_PORT,
                          MINIO_SECRET_KEY, MINIO_SECURE, logger)


def get_minio_client():
    minioClient = Minio(
        f"{MINIO_HOST}:{MINIO_PORT}",
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE)
    return minioClient


def download_from_minio(minio_client: Minio, bucket: str, object_name: str, local_path: str):
    minio_client.fget_object(bucket, object_name, local_path)


def upload_bytes_buffer_to_minio(minio_client: Minio, buffer, task_id, filename):
    buffer.seek(0)

    bucket_name = 'run-cases'
    object_name = f"{task_id}/{filename}"

    data_length = buffer.getbuffer().nbytes

    minio_client.put_object(
        bucket_name,
        object_name,
        data=buffer,
        length=data_length,
        content_type='video/webm'
    )

    return {"bucket": bucket_name, "file": object_name}
