import boto3
import os
from botocore.config import Config

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto"
    )

BUCKET = os.getenv("R2_BUCKET_NAME", "neuralwatch-recordings")

def upload_segment(file_path: str, r2_key: str) -> bool:
    try:
        client = get_r2_client()
        with open(file_path, "rb") as f:
            client.put_object(
                Bucket=BUCKET,
                Key=r2_key,
                Body=f,
                ContentType="video/MP2T"
            )
        return True
    except Exception as e:
        print(f"R2 upload error: {e}")
        return False

def upload_playlist(content: str, r2_key: str) -> bool:
    try:
        client = get_r2_client()
        client.put_object(
            Bucket=BUCKET,
            Key=r2_key,
            Body=content.encode("utf-8"),
            ContentType="application/vnd.apple.mpegurl"
        )
        return True
    except Exception as e:
        print(f"R2 playlist upload error: {e}")
        return False

def get_presigned_url(r2_key: str, expires_in: int = 3600) -> str:
    try:
        client = get_r2_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": r2_key},
            ExpiresIn=expires_in
        )
        return url
    except Exception as e:
        print(f"R2 presigned URL error: {e}")
        return ""

def delete_object(r2_key: str) -> bool:
    try:
        client = get_r2_client()
        client.delete_object(Bucket=BUCKET, Key=r2_key)
        return True
    except Exception as e:
        print(f"R2 delete error: {e}")
        return False

def list_segments(prefix: str) -> list:
    try:
        client = get_r2_client()
        response = client.list_objects_v2(
            Bucket=BUCKET,
            Prefix=prefix
        )
        return [obj["Key"] for obj in response.get("Contents", [])]
    except Exception as e:
        print(f"R2 list error: {e}")
        return []
