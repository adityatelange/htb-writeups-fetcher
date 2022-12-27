import json
import time
import os
import requests


from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

key = os.environ.get("KEY")
freeonly = os.environ.get("FREEONLY")

URLs = {
    "retired": "https://www.hackthebox.com/api/v4/machine/list/retired/paginated",
    "writeup": "https://www.hackthebox.com/api/v4/machine/writeup/{}",
}


def reQuester(url, params={}):
    r = requests.get(
        url,
        headers={
            "authority": "www.hackthebox.com",
            "authorization": "Bearer {}".format(key),
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": "https://app.hackthebox.com/",
            "origin": "https://app.hackthebox.com/",
            "accept": "application/json, text/plain, */*",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "accept-language": "en-US,en;q=0.9",
        },
        params=params,
    )
    return r


def download_file(url, Id, fileName):
    fetched_res = reQuester(url)

    # Retrieve HTTP meta-data
    if fetched_res.status_code == 200:
        # get the writeup filename
        filename = fetched_res.headers["Content-Disposition"].split("=")[1]

        with open(fileName, "wb") as f:
            # save the writeup file
            f.write(fetched_res.content)
        print("    [+] Downloaded {}".format(fileName))
        return "Downloaded"
    elif fetched_res.status_code == 404:
        # writeup does not exist on remote server
        print("    [-] Not Found {}".format(fileName))
        return "Not Found"
    elif fetched_res.status_code == 400:
        # writeup available to VIP subscribers
        if fetched_res.json() == {
            "message": "Writeups are available only to VIP Subscribers."
        }:
            print("    [-] VIP only {}".format(fileName))
            return "VIP only"
        else:
            print(Id, fetched_res.status_code, fetched_res.json())
            return "IDK"
    else:
        # 429 Too Many Requests, sleep for 50 sec
        print("[*] #{} sleeping for 50 sec code {}".format(Id, fetched_res.status_code))
        time.sleep(50)
        return "429"


if __name__ == "__main__":
    print("[+] Fetching writeups...")
    params = {"sort_type": "asc", "per_page": "100"}

    res = reQuester(URLs["retired"], params)

    if res.status_code == 401:
        print("[-] Unauthenticated.")
        exit(0)

    res = res.json()
    start_page = 1
    last_page = res["meta"]["last_page"]
    total = res["meta"]["total"]

    # store all boxes
    boxes = {}
    boxes_free = {}

    # iterate over all pages to fetch all writeups
    for current_page in range(start_page, last_page + 1):
        params["page"] = current_page
        print("    [+] Fetching page {}/{}".format(current_page, last_page))

        page_res = reQuester(url=URLs["retired"], params=params)
        data = page_res.json()["data"]

        for box in data:
            box_id = box["id"]
            # print(box)
            boxes[box_id] = {"name": box["name"], "status": "Pending"}

            if box["free"]:
                boxes_free[box_id] = {"name": box["name"], "status": "Pending"}

    print("[+] Free boxes: {}".format(boxes_free))

    # sort boxes ascending order by id https://stackoverflow.com/a/47017849/8291133
    boxes = dict(sorted(boxes.items()))

    with open("boxes.json", "w") as boxes_local:
        # save the writeup file
        json.dump(boxes, boxes_local, indent=4)

    print("[+] Boxes count matches with total? {}".format(len(boxes) == total))

    boxes_to_process = boxes

    if freeonly:
        boxes_to_process = boxes_free

    print("[+] Downloading Writeups")
    for box_id, box_details in boxes_to_process.items():
        fileName = "files/{}_{}.pdf".format(box_id, box_details["name"])

        # download only if we don't have it
        if not Path(fileName).is_file():
            d_status = download_file(
                URLs["writeup"].format(box_id),
                box_id,
                fileName,
            )

            box_details["status"] = d_status
            boxes[box_id] = box_details

            # 7 sec should be enough for not getting 429
            time.sleep(10)
        else:
            box_details["status"] = "Downloaded"
            boxes[box_id] = box_details

    with open("boxes.json", "w") as boxes_local:
        # save the writeup file
        json.dump(boxes, boxes_local, indent=4)
    print("[+] Done!")
