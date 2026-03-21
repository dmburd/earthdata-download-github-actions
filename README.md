# earthdata-download-github-actions

Downloading selected datasets (arrays) from [NASA Earthdata](https://www.earthdata.nasa.gov/) using GitHub Actions, with automatic upload of results to [Backblaze B2](https://www.backblaze.com/cloud-storage) cloud storage.

## How It Works

This repository provides a **GitHub Actions–based bot** that listens to GitHub Issues. When an authorized user posts a JSON request (specifying a geographic bounding box, date range, and desired data variables), the bot:

1. Searches NASA Earthdata for matching satellite tracks (e.g., GPM DPR data).
2. Downloads the relevant HDF5 arrays.
3. Generates an interactive HTML visualization (using Bokeh + Cartopy).
4. Uploads all results (HDF5 files, visualization, metadata) to a Backblaze B2 bucket.
5. Posts a summary comment back into the GitHub Issue.

---

## Prerequisites

Before setting up the workflow, you need the following accounts and resources:

### 1. GitHub Account

- You need a [GitHub](https://github.com/) account.
- **Forking this repository is mandatory** — the workflow runs via GitHub Actions in your own fork.

### 2. NASA Earthdata Account

- Register at [NASA Earthdata Login](https://urs.earthdata.nasa.gov/users/new).
- After registering, generate an **EDL (Earthdata Login) Bearer Token**:
  1. Log in to [https://urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov).
  2. Navigate to **"Generate Token"** (or visit [https://urs.earthdata.nasa.gov/documentation/for_users/user_token](https://urs.earthdata.nasa.gov/documentation/for_users/user_token)).
  3. Copy the generated token — you will need it for the `EDL_TOKEN` secret.

### 3. Backblaze B2 Account & Bucket

- Sign up at [Backblaze B2 Cloud Storage](https://www.backblaze.com/sign-up/cloud-storage).
- **Create a bucket**:
  1. In the B2 dashboard, go to **"Buckets"** → **"Create a Bucket"**.
  2. Choose a unique bucket name (e.g., `my-earthdata-results`).
  3. Set the bucket to **Private** (recommended).
- **Create an Application Key**:
  1. Go to **"App Keys"** → **"Add a New Application Key"**.
  2. You can restrict the key to your specific bucket for security.
  3. Save the **keyID** (Account ID) and **applicationKey** — you will need them for `B2_ACCOUNT_ID` and `B2_APPLICATION_KEY`.

---

## Setup: Fork & Configure

### Step 1 — Fork the Repository

> [!IMPORTANT]
> You **must** fork this repository to your own GitHub account. The workflow will not work on the original repo unless you are an owner/collaborator with access to its secrets.

1. Click the **"Fork"** button at the top-right of this repository page.
2. In your fork, go to **Settings → Actions → General** and ensure that **"Allow all actions and reusable workflows"** is selected.

### Step 2 — Configure Repository Secrets

Go to your fork's **Settings → Secrets and variables → Actions → Secrets** tab and add the following **repository secrets**:

| Secret Name | Description | Example (fake) |
|---|---|---|
| `USERNAMES_WHITELIST` | Comma-separated GitHub usernames allowed to trigger the bot (no spaces). | `johndoe,janedoe` |
| `EARTHDATA_LOGIN` | Your NASA Earthdata account login (email or username). | `john.doe@university.edu` |
| `EARTHDATA_PASSWORD` | Your NASA Earthdata account password. | `MySecureP@ssw0rd!` |
| `EDL_TOKEN` | Earthdata Login (EDL) Bearer Token for API authentication. | `eyJ0eXAiOiJKV1QiLCJhbGci...` (long JWT string) |
| `B2_BUCKET_NAME` | Name of your Backblaze B2 bucket where results will be uploaded. | `my-earthdata-results` |
| `B2_ACCOUNT_ID` | Backblaze B2 Application Key ID (keyID). | `004a1b2c3d4e5f0000000001` |
| `B2_APPLICATION_KEY` | Backblaze B2 Application Key (the secret key). | `K004xYzAbCdEfGhIjKlMnOpQrStUvWx` |
| `B2_SAVED_RESULTS_ROOTDIR` | Root directory path (prefix) inside your B2 bucket for saving results. | `EARTHDATA_AUTO_DNLD/` |

### Step 3 — Configure Repository Variables

Go to your fork's **Settings → Secrets and variables → Actions → Variables** tab and add the following **repository variable** (non-secret):

| Variable Name | Description | Example |
|---|---|---|
| `EARTHDATA_MAX_NUM_REQUESTS_PER_SEC` | Maximum number of concurrent requests per second to the Earthdata API. Recommended values: `40` or less. | `40` |

> [!NOTE]
> Variables (as opposed to secrets) are not masked in logs. `EARTHDATA_MAX_NUM_REQUESTS_PER_SEC` is safe to store as a variable because it contains no sensitive data.

---

## How to Trigger the Workflow

The workflow is triggered by **creating an issue** or **posting a comment** in the **Issues** tab of your forked repository.

### Trigger: Ask for Help

Create a new issue (or post a comment in an existing issue) with the body:

```
help
```

The bot will reply with a message showing the expected JSON format and supported parameters.

### Trigger: Submit a Data Request

Post a JSON object as the issue body or as a comment. The JSON specifies the geographic bounding box, time range, satellite product, and desired data variables.

**Example — GPM DPR radar reflectivity and precipitation rate:**

```json
{
    "lat_min": "59.5",
    "lat_max": "62.0",
    "lon_min": "29.5",
    "lon_max": "33.0",
    "date_min": "2026-01-01",
    "date_max": "2026-01-03",
    "product_short_name": "GPM_2ADPR",
    "product": "FS",
    "observable_vars": [
        "/FS/VER/sigmaZeroNPCorrected",
        "/FS/SLV/precipRateNearSurface"
    ]
}
```

**Example — GPM DPR Environmental product (surface wind):**

```json
{
    "lat_min": "59.5",
    "lat_max": "62.0",
    "lon_min": "29.5",
    "lon_max": "33.0",
    "date_min": "2026-01-01",
    "date_max": "2026-01-03",
    "product_short_name": "GPM_2ADPRENV",
    "product": "FS",
    "observable_vars": [
        "/FS/VERENV/surfaceWind"
    ]
}
```

> [!TIP]
> The JSON can be wrapped in a markdown code block (` ```json ... ``` `) — the bot will automatically extract it.

### Request Parameters Reference

| Parameter | Required | Default | Description |
|---|---|---|---|
| `lat_min` | ✅ | — | Minimum latitude of the bounding box (`-90` to `90`). |
| `lat_max` | ✅ | — | Maximum latitude of the bounding box (`-90` to `90`). |
| `lon_min` | ✅ | — | Minimum longitude of the bounding box (`-180` to `180`). |
| `lon_max` | ✅ | — | Maximum longitude of the bounding box (`-180` to `180`). |
| `date_min` | ✅ | — | Start date in `YYYY-MM-DD` format. |
| `date_max` | ✅ | — | End date in `YYYY-MM-DD` format. |
| `product_short_name` | ❌ | `GPM_2ADPR` | Earthdata product short name (e.g., `GPM_2ADPR`, `GPM_2ADPRENV`). |
| `product` | ✅ | — | Product identifier (e.g., `FS`). |
| `observable_vars` | ✅ | — | List of HDF5 variable paths to extract (e.g., `["/FS/VER/sigmaZeroNPCorrected"]`). |
| `product_idx_for_sigma_zero` | ❌ | `0` | Index for the last axis of sigmaZeroNPCorrected array. |
| `include_scan_time_arrays` | ❌ | `true` | Whether to include scan time arrays in output. |

### What Happens After Triggering

1. **Authorization check** — the bot verifies the comment author is in the `USERNAMES_WHITELIST`. Unauthorized users receive a rejection comment.
2. **Processing** — if authorized, the Python script runs: it queries Earthdata, downloads matching HDF5 data, generates visualizations, and uploads results to B2.
3. **Result comment** — the bot posts a comment with the number of tracks found and a list of saved output files:
   - `input_request.json` — the input parameters you provided.
   - `output_structure.json` — the structure of the saved output data.
   - `tracks_hdf5/*.HDF5` — downloaded HDF5 files with the requested arrays.
   - `few_tracks_visualized.html` — an interactive HTML visualization of a few tracks.

---

## Project Structure

```
.
├── .github/workflows/bot.yml   # GitHub Actions workflow definition
├── src/
│   ├── main.py                 # Entry point — parses input, orchestrates processing
│   ├── config.py               # Environment variable configuration
│   ├── pydantic_models.py      # Input validation models (Pydantic)
│   ├── get_earthdata_results.py# Earthdata search & download logic
│   └── utils/
│       ├── b2.py               # Backblaze B2 SDK integration
│       ├── s3.py               # S3-compatible upload utility
│       ├── save_output.py      # Saves HDF5 + visualization outputs
│       ├── visualization.py    # Visualization orchestration
│       ├── map_drawing_bokeh.py# Bokeh/Cartopy map drawing
│       └── common.py           # Shared helper functions
├── pyproject.toml              # Python project config & dependencies
├── .env.example                # Template for local environment variables
└── README.md
```

---

## Local Development (Optional)

If you want to run the script locally instead of via GitHub Actions:

1. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)** (the fast Python package manager).

2. **Fill in your credentials in `.env`:**

   The `.env` file is your **personal scratchpad** for local credentials — it is listed in `.gitignore` and never committed to version control. Copy the example template and fill in your real values:
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```
   The project uses [`python-dotenv`](https://pypi.org/project/python-dotenv/) to load `.env` automatically at startup, so no manual `export` commands are needed. In GitHub Actions, environment variables are injected from repository secrets instead, and the `.env` file is not present — `load_dotenv()` is a no-op in that context.

3. **Set the input payload and run:**
   ```bash
   export INPUT_PAYLOAD='{"lat_min":"59.5","lat_max":"62.0","lon_min":"29.5","lon_max":"33.0","date_min":"2026-01-01","date_max":"2026-01-03","product_short_name":"GPM_2ADPR","product":"FS","observable_vars":["/FS/VER/sigmaZeroNPCorrected"]}'
   uv run -m src.main
   ```
   *Note: `uv run` will automatically create and sync a virtual environment based on `pyproject.toml` — you do NOT need to create it manually.*

> [!CAUTION]
> The `.env` file contains real credentials. It is listed in `.gitignore` — **never commit it** to version control.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
