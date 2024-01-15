import requests
import json
from pprint import pprint
import logging

import os
from dotenv import load_dotenv
from os import environ
load_dotenv()


PROLIFIC_API_KEY = environ.get("PROLIFIC_API_KEY")
if not PROLIFIC_API_KEY:
    raise ValueError("PROLIFIC_API_KEY not set")

STUBURL = "https://app.prolific.co/submissions/complete?cc="
logger = logging.getLogger("benzapp.utils")

url = "https://api.prolific.co/api/v1/workspaces/647787b9fe04daac6e2e944e/balance/"

payload = ""
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Token {PROLIFIC_API_KEY}",
}


def get_url_for_image(player, img, extension=None):
    s3path = player.session.vars.get("s3path")
    extension = extension or player.session.vars.get("extension")
    full_path = f"{s3path}{img}.{extension}"
    return full_path


def get_balance():
    response = requests.request("GET", url, headers=headers, data=payload)
    if response.status_code != 200:
        logger.warning(f"Get error trying to get balance. Status code: {response.status_code}")
        return
    return response.json()


def get_study(study_id):
    url = f"https://api.prolific.co/api/v1/studies/{study_id}/"
    response = requests.request("GET", url, headers=headers, data=payload)
    if response.status_code != 200:
        logger.warning(f"Get error trying to get data for study {study_id}")
        return
    return response.json()


def get_completion_info(study_id):
    study_data = get_study(study_id)
    if study_data.get("error"):
        logger.warning(f"Get error trying to get data for study {study_id}")
        return
    completion_codes = study_data.get("completion_codes", [])

    # Find the first completion code with "COMPLETED" code_type
    completed_code = next(
        (code_info["code"] for code_info in completion_codes if code_info.get("code_type") == "COMPLETED"), "NO_CODE")

    full_return_url = f"{STUBURL}{completed_code}"
    logger.info(f"full_return_url: {full_return_url}; completed_code: {completed_code}")
    return dict(completion_code=completed_code, full_return_url=full_return_url)


def increase_space(study_id, num_extra, max_users):
    try:
        num_current_places = int(get_study(study_id).get("total_available_places"))
    except TypeError:
        logger.warning("SOMETHING WRONG WITH RESPONSE OF DATA GETTNG OF THE STUDY")
        return
    if num_current_places >= max_users:
        logger.warning(
            f"QUOTA EXCEEDED. Num of current places: {num_current_places}. Max users: {max_users}"
        )
        return
 
    url = f"https://api.prolific.co/api/v1/studies/{study_id}/"
    payload = json.dumps({"total_available_places": num_current_places + num_extra})
    logger.info(
        f"calling prolific api requesting to increase places to {num_current_places + num_extra} in a study {study_id}"
    )
    logger.info(f"payload: {payload}; url: {url}")
    response = requests.request("PATCH", url, headers=headers, data=payload)
    if response.status_code != 200:
        logger.warning(f"Get error trying to increase places in study {study_id}")
        return
    print('-' * 20)
    logger.info(f"response: {response}")
    logger.info(f"response.json(): {response.json()}")
    logger.info(f"response.text: {response.text}")
    logger.info(f'response.status_code: {response.status_code}')
    print('-'*20)
    return response.json()


pprint(get_balance())
if __name__ == "__main__":
 
    pprint(increase_space("61c1a16c9e1ee089d32f675b", 1, 15))
