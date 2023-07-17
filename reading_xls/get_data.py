import gspread
import pandas as pd
import json
from pprint import pprint
import gspread
import numpy as np
from collections import defaultdict
import re
import os
import base64
from pprint import pprint
from _secrets import data as google_creds

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

    sh = spreadsheet.worksheet(DATA_WS)

    data = sh.get_all_records()
    df = pd.DataFrame(data)
    df = creating_sentences(df)

    cols_to_keep = ["batch", "round", "id_in_group", "role", "to_whom", "overwrite"]

    # Define other columns you want to convert to dictionary
    cols_to_convert = [col for col in df.columns if col not in cols_to_keep]

    # Convert selected columns to a dictionary and store it as a JSON string
    df["data"] = df[cols_to_convert].apply(
        lambda row: json.dumps(row.to_dict()), axis=1
    )

    # Drop the converted columns from the DataFrame
    df.drop(columns=cols_to_convert, inplace=True)

    df = df.astype(data_types)
    df.role = df.role.astype("string")
    df.to_whom = (
        pd.to_numeric(df["to_whom"], errors="coerce", downcast="integer")
        .astype("Int64")
        .fillna(value=0)
    )
    df.overwrite = df.overwrite.astype("int").astype("bool")
    data = dict(data=df, settings=settings_dict, practice_settings=result_practice_dict)
    return data


if __name__ == "__main__":
    df = get_data("benz")
    pprint(df)
