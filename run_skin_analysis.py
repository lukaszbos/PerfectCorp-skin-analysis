import http.client
import json
import time
import os
from datetime import datetime

API_HOST = "yce-api-01.perfectcorp.com"
AUTH_TOKEN = "Bearer AgcErORSAAAAFnljZTozMTgzMjQ2OTI1OTczNDQwNTMAAAAAAAAAAQRq9F0KQAmGAAAAAAIAAAAAAAAAAAAAAAA=.UDeGaKsuioSOp3nUhVIxKa+z6tg="
POLL_INTERVAL_MS = 1000
MAX_RETRIES = 120


def create_new_file_obtain_file_id(image_path):
    print(f"Start File creation!")
    file_name = os.path.basename(image_path)
    file_size = os.path.getsize(image_path)
    payload = json.dumps({
        "files": [{
            "content_type": "image/jpeg",
            "file_name": file_name,
            "file_size": file_size
        }]
    })

    conn = http.client.HTTPSConnection(API_HOST)
    headers = {
        'Authorization': AUTH_TOKEN,
        'content-type': "application/json"
    }

    conn.request("POST", "/s2s/v1.1/file/skin-analysis", payload, headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    print(res.status, res.reason)
    print(data)

    response_json = json.loads(data)
    file_id = response_json["result"]["files"][0]["file_id"]
    url_to_upload = response_json["result"]["files"][0]["requests"][0]["url"]
    headers_to_upload = response_json["result"]["files"][0]["requests"][0]["headers"]
    content_length = headers_to_upload["Content-Length"]
    content_type = headers_to_upload["Content-Type"]
    print(f"File Created! Extracted file_id: {file_id}")
    

    with open(image_path, "rb") as image_file:
        file_data = image_file.read()  # Read the file as bytes
        conn2 = http.client.HTTPSConnection("yce-us.s3-accelerate.amazonaws.com")
        print(f"Url path {url_to_upload}")
        url_path = url_to_upload.split("yce-us.s3-accelerate.amazonaws.com")[1]
        print(f"Url path {url_path}")
        conn2.request("PUT", url_path, body=file_data, headers=headers_to_upload)
        res = conn2.getresponse()
        print(f"File Uploaded {file_id}")
        print(res.status, res.reason)
    
    
    
    return file_id


def run_skin_analisys_obtain_task_id(file_id):
    payload = json.dumps({
        "request_id": 0,
        "payload": {
            "file_sets": {
                "src_ids": [file_id]
            },
            "actions": [{
                "id": 0,
                "params": {},
                "dst_actions": ["hd_wrinkle", "hd_pore", "hd_texture", "hd_acne"]
            }]
        }
    })

    conn = http.client.HTTPSConnection(API_HOST)
    headers = {
        'Authorization': AUTH_TOKEN,
        'Content-Type': "application/json"
    }

    conn.request("POST", "/s2s/v1.0/task/skin-analysis", payload, headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    response_json = json.loads(data)
    task_id = response_json["result"]["task_id"]
    print(f"Extracted task_id: {task_id}")
    return task_id


def poll_task_status(task_id):
    conn = http.client.HTTPSConnection(API_HOST)
    headers = {'Authorization': AUTH_TOKEN}
    endpoint = f"/s2s/v1.0/task/skin-analysis?task_id={task_id}"
    print(f"Polling URL: https://{API_HOST}{endpoint}")

    for attempt in range(MAX_RETRIES):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            conn.request("GET", endpoint, headers=headers)
            res = conn.getresponse()
            data = res.read().decode("utf-8")
            response_json = json.loads(data)

            print(f"[{timestamp}] Attempt {attempt + 1}: Response: {response_json}")

            if response_json.get("status") == "done":
                print("Task completed.")
                return response_json

        except Exception as e:
            print(f"[{timestamp}] Attempt {attempt + 1}: Error occurred: {e}")

        time.sleep(POLL_INTERVAL_MS / 1000.0)

    print("Max retries reached. Task not completed.")
    return None



if __name__ == "__main__":
    image_path = r"C:\Users\lukas\Desktop\Skinally-2025\PerfectCorpAPI\mojafota-1900x1400.png"
    file_id = create_new_file_obtain_file_id(image_path)
    task_id = run_skin_analisys_obtain_task_id(file_id)
    result = poll_task_status(task_id)
    print("\nFinal Result:\n", json.dumps(result, indent=2))
