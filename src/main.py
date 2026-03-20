import json
import os
import re
import sys
from datetime import datetime

from pydantic import ValidationError

from src.get_earthdata_results import get_earthdata_results
from src.pydantic_models import EarthdataDownloadVisualizeServiceRequest
from src.utils.common import extract_track_number_from_h5_url_or_fpath
from src.utils.save_output import save_output_files


def main():
    # Get the comment text from environment variables
    payload = os.environ.get("INPUT_PAYLOAD", "")

    if not payload.strip():
        print("Error: No input data provided.")
        sys.exit(0)

    normalized_content = payload.strip().lower()

    if normalized_content == "help":
        print(
            "The required messages format can be understood from the examples below:\n\n"
            "```json\n"
            "{\n"
            '    "lat_min": "59.5",\n'
            '    "lat_max": "62.0",\n'
            '    "lon_min": "29.5",\n'
            '    "lon_max": "33.0",\n'
            '    "date_min": "2026-01-01",\n'
            '    "date_max": "2026-01-03",\n'
            '    "product_short_name": "GPM_2ADPR",\n'
            '    "product": "FS",\n'
            '    "observable_vars": [\n'
            '        "/FS/VER/sigmaZeroNPCorrected",\n'
            '        "/FS/SLV/precipRateNearSurface"\n'
            "    ]\n"
            "}\n"
            "```"
            "\n"
            "```json\n"
            "{\n"
            '    # coords and dates as above\n'
            '    "product_short_name": "GPM_2ADPRENV",\n'
            '    "product": "FS",\n'
            '    "observable_vars": [\n'
            '        "/FS/VERENV/surfaceWind"\n'
            "    ]\n"
            "}\n"
            "```"
        )
        sys.exit(0)

    request_params = None
    request_timestamp_str = None

    try:
        # Intelligently extract JSON from payload if it's wrapped in markdown or other text
        match = re.search(r'\{.*\}', payload, re.DOTALL)
        cleaned_payload = match.group(0) if match else payload

        json_data = json.loads(cleaned_payload)

        try:
            request_params = EarthdataDownloadVisualizeServiceRequest(**json_data)
            request_timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # print(f"OK, received a valid json with input parameters.\nTimestamp: `{request_timestamp_str}`.\nWait for the processing results.\n")
        except ValidationError as e:
            if all(err["type"] == "value_error" for err in e.errors()):
                error_msgs = []
                for err in e.errors():
                    field = ".".join(str(loc) for loc in err["loc"])
                    msg = err["msg"].replace("Value error, ", "")
                    error_msgs.append(f"- **{field}**: {msg}")
                error_details = "\n".join(error_msgs)
                print(f"ERROR, the provided parameters failed validation:\n\n{error_details}")
            else:
                print("ERROR, you have sent a json that does not conform to the required input parameters schema")
            sys.exit(0)
        except Exception:
            print("ERROR, you have sent a json that does not conform to the required input parameters schema")
            sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"DEBUG: Failed payload was:\n{repr(payload)}")
        print(f"DEBUG: Error details: {e}")
        print('ERROR, the received message is not a valid json neither the "help" word')
        sys.exit(0)

    track_fname_to_arr_dict = None
    if request_params:
        try:
            # Synchronous call since main is sync
            track_fname_to_arr_dict = get_earthdata_results(request_params, request_timestamp_str)
        except Exception as e:
            print(f"ERROR during processing the request:\n\n{str(e)}")
            sys.exit(0)

    if track_fname_to_arr_dict is not None and request_params is not None:
        track_fname_to_arr_dict = dict(
            sorted(
                track_fname_to_arr_dict.items(),
                key=lambda item: extract_track_number_from_h5_url_or_fpath(
                    item[0], request_params
                ),
            )
        )

    if request_params:
        if track_fname_to_arr_dict is not None:
            save_output_files(
                request_params,
                track_fname_to_arr_dict,
                request_timestamp_str,
            )

            saved_output_files_info = (
                f"The following files were saved to `<b2_saved_results_rootdir>/{request_timestamp_str}/`:\n"
                "- `input_request.json` — the input parameters that you provided\n"
                "- `output_structure.json` — the structure of the saved output data\n"
                "- `tracks_hdf5/*.HDF5` — the HDF5 files containing the requested arrays\n"
                "- `few_tracks_visualized.html` — the HTML file with a few tracks visualized\n"
            )

            track_numbers = sorted(
                [
                    extract_track_number_from_h5_url_or_fpath(fname, request_params)
                    for fname in track_fname_to_arr_dict.keys()
                ]
            )
            if len(track_numbers) > 7:
                display_tracks = track_numbers[:3] + ["..."] + track_numbers[-3:]
            else:
                display_tracks = track_numbers

            display_str = "[{}]".format(", ".join(display_tracks))
            print("The processing results are the following.")
            print(f"There are {len(track_numbers)} relevant tracks:\n{display_str}\n\n{saved_output_files_info}")
        else:
            print("No processing results to send / save")
            print("No relevant tracks found")


if __name__ == "__main__":
    main()
