import gspread
import pandas as pd
import json
import gspread
import re
import os
from pprint import pprint
import logging

logger = logging.getLogger("benzapp.get_data")
try:
    from .convert import convert
    from _secrets import data as google_creds
except (ModuleNotFoundError, ImportError):
    logger.warning("we run from main for debugging apparently")
    from convert import convert
    from dotenv import load_dotenv

    load_dotenv()
    with open("../_secrets/google_creds.json", "r") as f:
        data = json.load(f)
    data["private_key_id"] = os.getenv("GOOGLE_PRIVATE_KEY_ID")
    data["private_key"] = os.getenv("GOOGLE_PRIVATE_KEY")
    data["client_email"] = os.getenv("GOOGLE_CLIENT_EMAIL")
    data["client_id"] = os.getenv("GOOGLE_CLIENT_ID")
    google_creds = data

SETTINGS_WS = "settings"
DATA_WS = "data"
PRACTICE_WS_PREFIX = "practice_"
ALLOWED_WS_NAMES = set([SETTINGS_WS, DATA_WS])
data_types = {
    "round": int,
    "batch": int,
    "id_in_group": int,
    "role": str,
    "overwrite": int,
}


gc = gspread.service_account_from_dict(google_creds)


def creating_sentences(df):
    # Filter sentence columns
    sentence_columns = [col for col in df.columns if "sentence_" in col]

    df["sentence_data"] = df[sentence_columns].apply(
        lambda row: [
            [
                value
                for col, value in zip(sentence_columns, row)
                if col.split("_")[1] == str(i + 1)
            ]
            for i in range(int(max([col.split("_")[1] for col in sentence_columns])))
        ],
        axis=1,
    )

    # Drop the original sentence columns
    df.drop(columns=sentence_columns, inplace=True)
    return df


def convert_to_dict(json_str):
    try:
        return json.loads(json_str)
    except Exception as e:
        print(e)
        return {}


def get_data(filename):
    spreadsheet = gc.open(filename)

    # get practice settings:

    # Get all worksheets starting with 'practice_'
    practice_sheets = [
        ws
        for ws in spreadsheet.worksheets()
        if re.match(f"{PRACTICE_WS_PREFIX}\d+", ws.title)
    ]

    result_practice_dict = {}

    for ws in practice_sheets:
        # Get the worksheet

        # Get all values in the worksheet
        values = ws.get_all_values()
        # Convert the values to a pandas DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])
        # Convert the values to a pandas DataFrame
        practice_dict = {}
        pattern = r"_(\d+)$"
        for index, row in df.iterrows():
            key = row["name"]
            value = row["value"]

            if re.search(pattern, key):
                # Remove the trailing digits
                base_key = re.sub(pattern, "", key)
                if base_key not in practice_dict:
                    practice_dict[base_key] = []
                practice_dict[base_key].append(value)
            else:
                practice_dict[key] = value

        result_practice_dict[ws.title] = practice_dict
    print('-'*100)
    pprint(result_practice_dict)
    print('-'*100)

    wsh_names = set([i.title for i in spreadsheet.worksheets()])
    if not ALLOWED_WS_NAMES.issubset(wsh_names):
        raise Exception(
            f"Settings/Data spreadsheet should contain worksheets named {ALLOWED_WS_NAMES}"
        )

    settings_raw = spreadsheet.worksheet(SETTINGS_WS).get_all_values()
    settings_df = pd.DataFrame(settings_raw)
    settings_dict = (
        settings_df.set_index(settings_df.columns[0])
        .to_dict()
        .get(settings_df.columns[1])
    )
    settings_dict["suffixes"] = [
        value for key, value in settings_dict.items() if re.fullmatch("suffix_\d+", key)
    ]

    def allowed_value_converter(v):
        return [item.strip() for item in v.split(";")]

    settings_dict["allowed_values"] = [
        allowed_value_converter(value)
        for key, value in settings_dict.items()
        if re.fullmatch("allowed_values_\d+", key)
    ]
    settings_dict["interpreter_choices"] = allowed_value_converter(
        settings_dict["interpreter_choices"]
    )
    settings_dict["practice_pages"] = {
        key: bool(int(value))
        for key, value in settings_dict.items()
        if re.fullmatch("Practice\d+", key)
    }

    DATA_WS = "data"
    raw = spreadsheet.worksheet(DATA_WS).get_all_records()
    df = pd.DataFrame(raw)
    conv_data = convert(df)
    data = dict(
        data=conv_data,
        settings=settings_dict,
        practice_settings=result_practice_dict,
    )
    return data


def long_data(filename):
    spreadsheet = gc.open(filename)
    DATA_WS = "alt_data"
    raw = spreadsheet.worksheet(DATA_WS).get_all_records()
    df = pd.DataFrame(raw)
    conv_data = convert(df)
    return conv_data


def read_doc():
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials
    from googleapiclient.http import MediaIoBaseDownload
    from google.oauth2.service_account import Credentials
    import io

    creds = Credentials.from_service_account_info(
        google_creds, scopes=["https://www.googleapis.com/auth/drive"]
    )
    
    
    # Build the service
    drive_service = build('drive', 'v3', credentials=creds)

    # The ID of your Google Doc
    file_id = "1frtr8zzT1KehperGjaNJNKgEh9fpZvHc0OvPuUgPblo"

    # Use the 'files.get' method to retrieve the file's metadata
    # Define the mimeType for HTML
    mimeType = 'text/html'

    # Use the 'files.export_media' method to download the file as HTML
    request = drive_service.files().export_media(fileId=file_id, mimeType=mimeType)

    # Create an in-memory binary stream to hold the downloaded file
    fh = io.BytesIO()

    # Initialize a media download object
    downloader = MediaIoBaseDownload(fd=fh, request=request)

    # Perform the download
    done = False
    while not done:
        status, done = downloader.next_chunk()

    # The file content is now in 'fh', which you can read and decode as HTML
    html_content = fh.getvalue().decode('utf-8')
    return (html_content)
    # The link to download the file as HTML is under the 'text/html' key
    # html_link = export_links.get('text/html')

    # print(html_link)


if __name__ == "__main__":
    # read_doc()
    df = get_data("marbExpFullEN_1").get('data')
    pprint(df.shape)
    # df = long_data("benz")
    # pprint(df.shape)
    df.to_csv("./mock.csv", index=False)
