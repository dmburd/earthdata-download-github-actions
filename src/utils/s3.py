import boto3

s3_client = boto3.client(
    "s3",
    endpoint_url="https://s3.us-west-004.backblazeb2.com",  # Replace with your B2 region's endpoint
    aws_access_key_id="YOUR_KEY_ID",
    aws_secret_access_key="YOUR_APPLICATION_KEY",
)

local_file_path = "path/to/your/local_artifact.HDF5"
bucket_name = "your-bucket-name"
b2_file_name = "remote_folder/remote_artifact.HDF5"

s3_client.upload_file(local_file_path, bucket_name, b2_file_name)
