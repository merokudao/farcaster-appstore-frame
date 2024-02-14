
import os
import pathlib
import random
from typing import Any, Dict, List, Union
import requests
import json
from threading import Thread
import concurrent.futures
import queue
from pycaster.lib.utils import setup_logger
from pycaster.lib.io import r


__current_file_path__ = pathlib.Path(__file__).resolve()
__current_dir__ = __current_file_path__.parent

logger = setup_logger(__name__)


class FCUser:

  @staticmethod
  def get_user_data(fid: int):
    """
    Returns the user data for a given fid
    """
    if not isinstance(fid, int):
      raise ValueError("fid must be an integer")
    cache_key = f"user_data:{fid}"
    logger.info(f"Attempting to get Cache Key: {cache_key}")
    cached_value = r.get(cache_key)
    if cached_value:
      logger.debug(f"Returning User Data from cache: {cached_value}")
      return json.loads(cached_value)

    url = f"https://api.neynar.com/v2/farcaster/user/bulk?fids={fid}&viewer_fid={fid}"


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
        if len(users) == 1:
          r.setex(cache_key, 20*60, json.dumps(users[0]))
          logger.info("Returning user data from Neynar v2")
          return users[0]
        else:
          logger.info(f"Error fetching user data from Neynar v2: {response.text}")
          logger.info(response.text, response.status_code)
          return None
    else:
      logger.info(f"Error fetching user data from Neynar v2: {response.text}")
      logger.info(response.text, response.status_code)
      return None

  @staticmethod
  def get_users_data(fids: List[int]) -> Dict[int, Any]:
    """
    Fetches user data for a list of fids in parallel and returns a dictionary
    with fids as keys and user objects (or errors) as values.
    """
    # This dictionary will store the final results
    results = {}

    # Define a helper function to handle the fetching for one fid
    # This will allow error handling for individual requests
    def fetch_data(fid):
        try:
            return fid, FCUser.get_user_data(fid)
        except Exception as e:
            logger.error(f"Error fetching data for fid {fid}: {e}")
            return fid, None  # or return an error message specific to the failure

    # Use ThreadPoolExecutor to run get_user_data in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Schedule the execution of fetch_data for each fid
        # and collect the future objects in a list
        futures = [executor.submit(fetch_data, fid) for fid in fids]

        # As each future completes, process its result
        for future in concurrent.futures.as_completed(futures):
            fid, user_data = future.result()
            results[fid] = user_data

    return results

  @staticmethod
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

  @staticmethod
  def get_fid(username: str):
      cache_key = f"username:{username}"
      cached_value = r.get(cache_key)
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
              r.set(cache_key, users[0]['fid'])
              return users[0]['fid']
          else:
              return None

  @staticmethod
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
              logger.info(f"Failed to fetch channel follow data: {response.status_code}")
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

  @staticmethod
  def get_followers(fid: int, limit = 30):
    limit = max(150, limit)
    cache_key = f"followers:{fid}_{limit}"
    cached_data = r.get(cache_key)
    if cached_data:
        # If cached data exists, return it after loading from JSON string
        logger.info("Followers Returning from cache")
        return json.loads(cached_data)

    base_url = "https://api.neynar.com/v1/farcaster/followers"
    params = {
      "fid": fid,
      "viewerFid": fid,
      "limit": limit
    }

    headers = {
        "accept": "application/json",
        "api_key": os.getenv("NEYNAR_API_KEY")
    }

    response = requests.get(base_url, headers=headers, params=params)
    if response.status_code == 200:
      data = response.json()
      users = data["result"].get("users", [])
      r.setex(cache_key, 600, json.dumps(users))
      # Also set the cache for the user's followers username, userid relation
      for user in users:
          r.set(f"username:{user['username']}", user['fid'])
          cache_key = f"user_data:{user['fid']}"
          cache_val = json.dumps(user)
          logger.info(f"Setting cache::{ cache_key } with value: {cache_val}")
          r.setex(cache_key, 60*20, cache_val)
      logger.info("Followers returning from API")
      return users
    else:
      return []

  @staticmethod
  def get_random_follower(fid: int):
    followers = FCUser.get_followers(fid)
    if len(followers) > 0:
      random_idx = random.randint(0, len(followers) - 1)
      logger.debug(f"Random index: {random_idx}")
      return followers[random_idx]
    return None

  @staticmethod
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

  @staticmethod
  def user_has_casted(fid: int, cast_text: str, count = 10) -> bool:
    casts = FCUser.get_casts(fid, count)
    for cast in casts:
      if cast_text in cast:
        return True
    return False

  @staticmethod
  def clean_username(username: str):
    if username.startswith("@"):
      username = username[1:]
    elif username.startswith("https://warpcast.com/"):
      username = username.split("/")[-1]
    return username

class MintCriterion:

  def __init__(self, follow_channel: str = None,
              follow_user: str = None,
              cast_text: str = None,
              casts_to_check = 10) -> None:
    """
    The conditions for Mint
    follow_channel: Must follow this channel (specified by channel id).
    follow_user: Must follow this user (specified by username or fid).
    cast_text: This text must be present in the last few casts.
    casts_to_check: The last `casts_to_check` casts of the user will be
      checked for the `cast_text` to be present.
    """
    self.follow_channel = follow_channel
    self.follow_user = follow_user
    self.cast_text = cast_text
    self.casts_to_check = casts_to_check

  @staticmethod
  def check_mint_criteria(fid: int, criterion):
      # Queue to store results
      results_queue = queue.Queue()

      # Wrapper function to execute check, store result, and criterion name in queue
      def execute_check(check_func, criterion_name, *args):
          result = check_func(*args)
          results_queue.put((result, criterion_name))

      # List to hold all the threads
      threads = []

      if criterion.follow_channel is not None:
          thread = Thread(target=execute_check, args=(FCUser.user_follows_channel, 'follow_channel', criterion.follow_channel, fid))
          threads.append(thread)

      if criterion.follow_user is not None:
          thread = Thread(target=execute_check, args=(FCUser.user_follows_user, 'follow_user', fid, criterion.follow_user))
          threads.append(thread)

      if criterion.cast_text is not None:
          thread = Thread(target=execute_check, args=(FCUser.user_has_casted, 'cast_text', fid, criterion.cast_text, criterion.casts_to_check))
          threads.append(thread)

      # Start all threads
      for thread in threads:
          thread.start()

      # Wait for all threads to complete
      for thread in threads:
          thread.join()

      # Process results to determine which criteria were not fulfilled
      failed_criteria: List[str] = []
      for _ in range(len(threads)):
          result, criterion_name = results_queue.get()
          if not result:
              failed_criteria.append(criterion_name)

      # Determine if all criteria were fulfilled
      all_criteria_fulfilled = len(failed_criteria) == 0

      # Return whether all criteria were fulfilled and the list of failed criteria
      return all_criteria_fulfilled, failed_criteria
