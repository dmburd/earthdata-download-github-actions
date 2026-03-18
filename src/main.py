import json
import os
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
        print("The required messages format can be seen from an example below:\n")
        print("```json")
        print("{")
        print('    "lat_min": "59.5",')
        print('    "lat_max": "62.0",')
        print('    "lon_min": "29.5",')
        print('    "lon_max": "33.0",')
        print('    "date_min": "2026-01-01",')
        print('    "date_max": "2026-01-03",')
        print('    "product": "FS",')
        print('    "observable_vars": [')
        print('        "/FS/VER/sigmaZeroNPCorrected"')
        print("    ]")
        print("}")
        print("```")
        sys.exit(0)

    request_params = None
    request_timestamp_str = None

    try:
        json_data = json.loads(payload)

        try:
            request_params = EarthdataDownloadVisualizeServiceRequest(**json_data)
            request_timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            print(f"OK, received a valid json with input parameters.\nTimestamp: `{request_timestamp_str}`.\nWait for the processing results.\n")
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

    except json.JSONDecodeError:
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
            # save_output_files(
            #     request_params,
            #     track_fname_to_arr_dict,
            #     request_timestamp_str,
            # )

            saved_output_files_info = (
                f"The following files were saved to `<saved_results_rootdir>/{request_timestamp_str}/`:\n"
                "- `input_request.json` — the input parameters that you provided\n"
                "- `output_dict_structure.json` — the structure of the saved dict object (`track_fname_to_arr_dict`)\n"
                "- `track_fname_to_arr_dict.npz` — the dictionary mapping track filenames to array dicts\n"
                "- `few_tracks_visualized.html` — the HTML file with a few tracks visualized\n\n"
                "Read the contents of the file `track_fname_to_arr_dict.npz` in the following way:\n"
                "```python\n"
                "track_fname_to_arr_dict = np.load(\n"
                "    'track_fname_to_arr_dict.npz',\n"
                "    allow_pickle=True\n"
                ")\n"
                "track_fname_to_arr_dict = {\n"
                "    k: v.item()\n"
                "    for k, v in track_fname_to_arr_dict.items()\n"
                "}\n"
                "```"
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
            print(f"There are {len(track_numbers)} relevant tracks:\n{display_str}\n\n{saved_output_files_info}")
        else:
            print("No processing results to send / save")
            print("No relevant tracks found")


if __name__ == "__main__":
    main()
