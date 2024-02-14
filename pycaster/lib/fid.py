
import os
import pathlib
from typing import List, Union
import requests
import json
from urllib.parse import quote

from pycaster.lib.utils import setup_logger
from pycaster.lib.io import r


__current_file_path__ = pathlib.Path(__file__).resolve()
__current_dir__ = __current_file_path__.parent

logger = setup_logger(__name__)

def get_user_data(fids: Union[List[int], int]):
  """
  Returns the user data for a given fid
  """
  if isinstance(fids, int):
    fids = [fids]

  _fids = ",".join([str(x) for x in fids])
  _fids = quote(_fids)
  cached_value = r.get(_fids)
  if cached_value:
    # current_app.logger.info(f"Returning from cache: {cached_value}")
    return json.loads(cached_value)

  url = f"https://api.neynar.com/v2/farcaster/user/bulk?fids={_fids}&viewer_fid={fids[0]}"


  # current_app.logger.info(os.getenv("NEYNAR_API_KEY"))
  headers = {
      "accept": "application/json",
      "api_key": os.getenv("NEYNAR_API_KEY")
  }

  response = requests.get(url, headers=headers)

  if response.status_code == 200:
    user_data = response.json()
    if "users" in user_data:
      users = user_data["users"]
      if len(users) > 0:
        user_dict = {int(user['fid']): user for user in users}
        r.setex(_fids, 20*60, json.dumps(user_dict))
        # current_app.logger.info(user_dict)
        return user_dict
      else:
        # current_app.logger.info(f"Error fetching user data from Neynar v2: {response.text}")
        # current_app.logger.info(response.text, response.status_code)
        return None
  else:
    # current_app.logger.info(f"Error fetching user data from Neynar v2: {response.text}")
    # current_app.logger.info(response.text, response.status_code)
    return None


def get_casts(fid: int, limit = 10):
  """
  Returns the text of casts for a given fid
  """
  url = f"https://api.neynar.com/v1/farcaster/casts?fid={fid}&viewerFid={fid}&limit={limit}"

  headers = {
      "accept": "application/json",
      "api_key": os.getenv("NEYNAR_API_KEY")
  }

  response = requests.get(url, headers=headers)

  if response.status_code == 200:
    casts_data = response.json()
    casts = casts_data["result"]["casts"]
    return [x['text'] for x in casts]
  else:
    # current_app.logger.info(f"Error fetching casts from Neynar v2: {response.text}")
    return []

def get_fid(username: str):
    cached_value = r.get(username)
    if cached_value is not None:
        return int(cached_value)

    url = f"https://api.neynar.com/v2/farcaster/user/search?q={username}&viewer_fid=1"

    headers = {
        "accept": "application/json",
        "api_key": os.getenv("NEYNAR_API_KEY")
    }

    response = requests.get(url, headers=headers)

    response = response.json()
    if 'result' in response and 'users' in response['result']:
        users = response['result']['users']
        if len(users) > 0:
            r.set(username, users[0]['fid'])
            return users[0]['fid']
        else:
            return None

def user_follows_channel(channel_name: str,
                         fid: Union[int, None] = None,
                         username: Union[str, None] = None) -> bool:
    """
    This method is painfully slow for channels with large number of
    followers (> 5K).
    For followers ~ 1-2K it's fine, but anything more than that
    it breaks
    """
    base_url = "https://api.neynar.com/v2/farcaster/channel/followers"
    params = {"id": channel_name, "limit": 1000}
    headers = {
        "accept": "application/json",
        "api_key": os.getenv("NEYNAR_API_KEY")
    }

    user_exists = False
    while True:
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch data: {response.status_code}")
            break
        data = response.json()
        users = data.get("users", [])

        # Check if user exists in the current batch
        for user in users:
            if fid and user["fid"] == fid:
                user_exists = True
                break
            if username and user["username"].lower() == username.lower():
                user_exists = True
                break

        if user_exists:
            break

        # Prepare for the next iteration
        next_cursor = data.get("next", {}).get("cursor")
        if not next_cursor:
            break  # Exit loop if there is no next cursor

        params["cursor"] = next_cursor  # Update cursor for the next request

    return user_exists


def user_follows_user(fid: int, fid2: int = None, username2: str = None) -> bool:

    base_url = "https://api.neynar.com/v1/farcaster/following"
    params = {
      "fid": fid,
      "viewerFid": fid,
      "limit": 150
    }

    headers = {
        "accept": "application/json",
        "api_key": os.getenv("NEYNAR_API_KEY")
    }
    user_follows = False
    while True:
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch data: {response.status_code}")
            break
        data = response.json()
        users = data.get("users", [])

        # Check if user exists in the current batch
        for user in users:
            if fid2 and user["fid"] == fid2:
                user_follows = True
                break
            if username2 and user["username"].lower() == username2.lower():
                user_follows = True
                break

        if user_follows:
            break

        # Prepare for the next iteration
        next_cursor = data.get("next", {}).get("cursor")
        if not next_cursor:
            break  # Exit loop if there is no next cursor

        params["cursor"] = next_cursor  # Update cursor for the next request

    return user_follows
