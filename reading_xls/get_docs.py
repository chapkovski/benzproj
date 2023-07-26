from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import requests
def get_doc(filename):


    drive_service = build('drive', 'v3', credentials=creds)  # Assuming 'creds' is your OAuth 2.0 credentials
    file_id = 'your-google-doc-id'  # The ID of your Google Doc

    request = drive_service.files().get(fileId=file_id)
    file = request.execute()

    export_link = file.get('exportLinks').get('text/html')

    headers = {
        'Authorization': 'Bearer ' + creds.token
    }

    response = requests.get(export_link, headers=headers)

    html_content = response.text

if __name__ == "__main__":
    print('hellow')    