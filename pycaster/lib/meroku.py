import http.client
import json
import os

from pycaster.lib.utils import setup_logger
from pycaster.lib.io import r

logger = setup_logger(__name__)

def get_apps():
  cache_key = "farcaster:apps"
  cached_val = r.get(cache_key)
  if cached_val:
    return json.loads(cached_val)

  conn = http.client.HTTPSConnection("api.meroku.store")

  headers = {
      'Accept': "application/json",
      'apikey': os.getenv("MEROKU_API_KEY")
  }

  conn.request("GET", "/api/v1/dapp/search?storeKey=farcaster", headers=headers)

  res = conn.getresponse()
  logger.info(f"Meroku API response: {res.status}")
  if res.status != 200:
    return []

  data = res.read()
  data = json.loads(data)["data"]
  r.set(cache_key, json.dumps(data), ex=60*60*12)
  return data

def rate_app(appId: str, rating: int, fid: int):
  conn = http.client.HTTPSConnection("api.meroku.store")
  payload = {
    "dappId": appId,
    "rating": rating,
    "comment": "",
    "userId": f"fid:{ fid }",
    "userAddress": "",
    "version": ""
  }

  headers = {
      'Content-Type': "application/json",
      'Accept': "application/json",
      'apikey': os.getenv("MEROKU_API_KEY")
  }

  conn.request("POST", "/api/v1/dapp/rate", json.dumps(payload), headers)

  res = conn.getresponse()
  if res.status != 200:
    return []

  data = res.read()
  data = json.loads(data)
  return data
