import os

from dotenv import load_dotenv
from nanoid_dictionary import lowercase, numbers, uppercase

NANOID_ALPHABET = numbers + uppercase + lowercase
NANOID_SIZE = 21

load_dotenv()

SAVED_RESULTS_ROOTDIR = os.getenv("SAVED_RESULTS_ROOTDIR")

NTFY_SH_TOPIC_URL = os.getenv("NTFY_SH_TOPIC_URL")

EARTHDATA_LOGIN = os.getenv("EARTHDATA_LOGIN")
EARTHDATA_PASSWORD = os.getenv("EARTHDATA_PASSWORD")
EDL_TOKEN = os.getenv("EDL_TOKEN")

EARTHDATA_MAX_NUM_REQUESTS_PER_SEC = int(os.getenv("MAX_NUM_REQUESTS_PER_SEC", 50))
