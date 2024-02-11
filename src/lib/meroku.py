import http.client
import json

def get_apps():
  conn = http.client.HTTPSConnection("api.meroku.store")

  headers = {
      'Accept': "application/json",
      'apikey': "123"
  }

  conn.request("GET", "/api/v1/dapp/search?storeKey=farcaster", headers=headers)

  res = conn.getresponse()
  if res.status != 200:
    return []

  data = res.read()
  data = json.loads(data)["data"]
  return data