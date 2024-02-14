import base64
import os
import pathlib
import requests
import json
from openai import OpenAI
import boto3
import redis
from io import BytesIO
from botocore.exceptions import NoCredentialsError
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

from .utils import get_numeric_env_var, setup_logger


__current_file_path__ = pathlib.Path(__file__).resolve()
__current_dir__ = __current_file_path__.parent

logger = setup_logger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "dappstoreapp")

def get_s3_client():
  aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
  aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

  # Create an S3 client
  s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
  )

  return s3_client


def upload_png_to_s3(png_buffer, hash_key):
    """
    Uploads a PNG buffer to AWS S3.

    Parameters:
    - png_buffer: BytesIO object containing PNG data.
    - bucket_name: Name of the S3 bucket to upload to.
    - file_name: S3 key name under which the PNG file will be saved.
    """
    s3_client = get_s3_client()
    try:
        # Rewind the buffer to the beginning before uploading
        png_buffer.seek(0)
        file_name = f"roastme/{hash_key}.png"
        # Upload the PNG data to S3
        s3_client.upload_fileobj(png_buffer, S3_BUCKET_NAME, file_name)
        # current_app.logger.info(f"File {file_name} uploaded to {S3_BUCKET_NAME} successfully.")

        # The base S3 URL
        f"https://dappstoreapp.s3.us-west-2.amazonaws.com/{file_name}.png"

        # The CDN Url
        return f"https://d7aseyv2y654x.cloudfront.net/{file_name}.png"
    except NoCredentialsError:
        # current_app.logger.info("Credentials not available")
       print("sd")
    except Exception:
        # current_app.logger.info(f"Failed to upload file to S3: {e}")
        print("sdd")

def get_external_image(url):
    # Use the URL as the key to check in Redis
    cache_key = f"pfp:test1:{url}"
    cached_image = r.get(cache_key)

    if cached_image:
        # current_app.logger.debug("Returning from cache")
        # If found in cache, decode and load the image
        img_data = base64.b64decode(cached_image)
        img = Image.open(BytesIO(img_data))
    else:
        # If not found in cache, fetch the image, cache it, and return
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        print(f"Image format: {img.format}")
        if img.format == 'JPEG':
          img_png = img.convert("RGBA")
          buffered_png = BytesIO()
          img_png.save(buffered_png, format="PNG")
          img = Image.open(BytesIO(buffered_png.getvalue()))

        print(f"Converted Image format: {img.format}")

        # Serialize and store the image in Redis
        buffered = BytesIO()
        img_format = img.format if img.format else 'PNG'
        img.save(buffered, format=img_format)
        img_base64 = base64.b64encode(buffered.getvalue())
        r.setex(cache_key, 20*60, img_base64)

    return img

def get_external_images(input):
    """Fetches profile images from a URL or a list of URLs.

    Args:
        input (str or list): A single URL string or a list of URL strings.

    Returns:
        Image.Image or list of Image.Image: The fetched profile image(s).
    """
    if isinstance(input, str):
        # Single URL, fetch directly.
        return get_external_image(input)
    elif isinstance(input, list):
        # List of URLs, fetch in parallel.
        with ThreadPoolExecutor() as executor:
            images = list(executor.map(get_external_image, input))
        return images
    else:
        raise ValueError("Input must be a string URL or a list of string URLs.")

def upload_svg_to_s3(file_text, object_name):
  """
  Uploads SVG content to an S3 bucket.

  Parameters:
  - file_text: A string containing the SVG file content.
  - bucket_name: The name of the S3 bucket.
  - object_name: The S3 object name under which the file should be stored.

  Returns:
  - True if file was uploaded, else False.
  """
  s3_client = get_s3_client()

  object_name = f"roastme/{object_name}.svg"

  try:
    # Upload the SVG content to S3
    s3_client.put_object(Body=file_text, Bucket=S3_BUCKET_NAME,
                         Key=object_name, ContentType='image/svg+xml')
    # current_app.logger.info(f"File {object_name} uploaded to {S3_BUCKET_NAME}.")
    # return f"https://dappstoreapp.s3.us-west-2.amazonaws.com/{object_name}.svg"
    return f"https://d7aseyv2y654x.cloudfront.net/{object_name}.svg"
  except NoCredentialsError:
    # current_app.logger.info("Credentials not available.")
    return False

def upload_json_to_s3(json_obj, object_name):
  s3_client = get_s3_client()

  object_name = f"roastme/{object_name}.json"

  try:
    # Upload the SVG content to S3
    s3_client.put_object(Body=json.dumps(json_obj), Bucket=S3_BUCKET_NAME,
                         Key=object_name, ContentType='application/json')
    # current_app.logger.info(f"File {object_name} uploaded to {S3_BUCKET_NAME}.")
    # return f"https://dappstoreapp.s3.us-west-2.amazonaws.com/{object_name}.json"
    return f"https://d7aseyv2y654x.cloudfront.net/{object_name}.json"
  except NoCredentialsError:
    # current_app.logger.info("Credentials not available.")
    return False

def get_openai_response_json(prompt: str):
  response = client.chat.completions.create(
      messages=[{
        "role": "user",
        "content": prompt
        }],
      response_format={ "type": "json_object" },
      model="gpt-3.5-turbo-0125"
    )

  response = response.choices[0].message.content
  response = json.loads(response)
  return response

r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'),
                port=get_numeric_env_var('REDIS_PORT',6379),
                username=os.getenv('REDIS_USERNAME', None),
                password=os.getenv('REDIS_PASSWORD', None),
                db=0,
                protocol=3)
