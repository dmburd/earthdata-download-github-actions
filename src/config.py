import os

from dotenv import load_dotenv

# Loads variables from .env when running locally; no-op in GitHub Actions
# (where env vars are injected from repository secrets/variables).
load_dotenv()

LOCAL_SAVED_RESULTS_ROOTDIR = os.getcwd()
B2_SAVED_RESULTS_ROOTDIR = os.getenv("B2_SAVED_RESULTS_ROOTDIR")

EARTHDATA_LOGIN = os.getenv("EARTHDATA_LOGIN")
EARTHDATA_PASSWORD = os.getenv("EARTHDATA_PASSWORD")
EDL_TOKEN = os.getenv("EDL_TOKEN")

EARTHDATA_MAX_NUM_REQUESTS_PER_SEC = int(os.getenv("EARTHDATA_MAX_NUM_REQUESTS_PER_SEC", 50))

B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")
B2_ACCOUNT_ID = os.getenv("B2_ACCOUNT_ID")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
