import os
import pathlib
import logging


__current_file_path__ = pathlib.Path(__file__).resolve()
__current_dir__ = __current_file_path__.parent

prod = os.getenv("ENV") == "prod"
stag = os.getenv("ENV") == "staging"
app_url = os.getenv("APP_URL", "testroast.ngrok.app")

def setup_logger(name):
    logger = logging.getLogger(name)
    log_level = os.getenv("LOG_LEVEL")
    if log_level:
        logger.setLevel(log_level)
    else:
      logger.setLevel(logging.INFO if prod else logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger

def get_numeric_env_var(env_var_name, default_value):
  try:
    # Try to retrieve and convert the environment variable to an integer
    return int(os.getenv(env_var_name, default_value))
  except ValueError:
    # If conversion fails, return the default value
    return default_value

