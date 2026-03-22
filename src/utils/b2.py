from b2sdk.v2 import B2Api, InMemoryAccountInfo
from loguru import logger

from src.config import B2_ACCOUNT_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME

B2_BUCKET = None

if B2_ACCOUNT_ID and B2_APPLICATION_KEY and B2_BUCKET_NAME:
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", B2_ACCOUNT_ID, B2_APPLICATION_KEY)
        B2_BUCKET = b2_api.get_bucket_by_name(B2_BUCKET_NAME)
    except Exception as e:
        logger.warning(f"B2 initialization failed — uploads to B2 will be skipped: {e}")
else:
    logger.info("B2 credentials not configured — uploads to B2 will be skipped.")
