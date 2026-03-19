from b2sdk.v2 import InMemoryAccountInfo, B2Api
from src.config import B2_BUCKET_NAME, B2_ACCOUNT_ID, B2_APPLICATION_KEY

info = InMemoryAccountInfo()
b2_api = B2Api(info)

b2_api.authorize_account("production", B2_ACCOUNT_ID, B2_APPLICATION_KEY)

B2_BUCKET = b2_api.get_bucket_by_name(B2_BUCKET_NAME)
