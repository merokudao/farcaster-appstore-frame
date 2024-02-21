from flask import request
from pycaster.lib.utils import setup_logger
from pycaster.lib.io import validate_message_hub
from pycaster.lib.fid import FCUser
from threading import Thread

logger = setup_logger(__name__)

def fetch_followers_in_background(fid):
    # This function will run in a separate thread
    try:
        FCUser.get_followers(fid)
    except Exception as e:
        logger.error(f"Error fetching followers: {e}")

def get_users_details_in_background(user_id: int):
    # This function will run in a separate thread
    try:
        FCUser.get_user_data(user_id)
    except Exception as e:
        logger.error(f"Error fetching user data: {e}")

def validate_request(data):
    if 'trustedData' in data and 'messageBytes' in data['trustedData']:
        validate_response = validate_message_hub(bytes.fromhex(data['trustedData']['messageBytes']))
        if 'valid' in validate_response and validate_response['valid']:
            _msg_data = validate_response['message']['data']
            logger.debug(f"Validated message: {_msg_data}")
            if _msg_data['fid'] == data['untrustedData']['fid']:
                return True
            return True
    return False

def check_trusted_data():
    # Only apply the check to POST requests
    if request.method == 'POST':
        json_data = request.get_json(silent=True) or {}
        logger.info(json_data)
        fid = json_data.get('untrustedData', {}).get('fid')
        if fid:
            Thread(target=fetch_followers_in_background,
                   args=(fid,),
                   daemon=True).start()
            Thread(target=get_users_details_in_background,
                    args=(fid,),
                    daemon=True).start()
        return validate_request(json_data)

    return True
