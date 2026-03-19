from b2sdk.v2 import InMemoryAccountInfo, B2Api
from src.config import B2_BUCKET_NAME, B2_ACCOUNT_ID, B2_APPLICATION_KEY

info = InMemoryAccountInfo()
b2_api = B2Api(info)

# Authorize with your B2 application credentials
b2_api.authorize_account("production", B2_ACCOUNT_ID, B2_APPLICATION_KEY)

# Get the bucket by name and upload your local file
B2_BUCKET = b2_api.get_bucket_by_name(B2_BUCKET_NAME)
#print(f"{B2_BUCKET=}")
# local_file_path = "path/to/your/local_artifact.HDF5"
# b2_file_name = "remote_folder/remote_artifact.HDF5"

# bucket.upload_local_file(
#     local_file=local_file_path,
#     file_name=b2_file_name,
# )
#breakpoint()
