# This is to keep google credentials safe
import json
import os
from pprint import pprint
with open("_secrets/google_creds.json", "r") as f:
    data = json.load(f)
    data["private_key_id"]=os.getenv('GOOGLE_PRIVATE_KEY_ID')
    data["private_key"]=os.getenv('GOOGLE_PRIVATE_KEY')
    data["client_email"]=os.getenv('GOOGLE_CLIENT_EMAIL')
    data["client_id"]=os.getenv('GOOGLE_CLIENT_ID')
