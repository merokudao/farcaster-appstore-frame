import random
from urllib.parse import quote
from flask import Flask, render_template, request, redirect, send_file, url_for

from pycaster.lib.image import ImageComponent, generate_app_image
from pycaster.lib.meroku import get_apps, rate_app
from pycaster.lib.middleware import check_trusted_data
from pycaster.lib.utils import app_url, setup_logger

app = Flask(__name__, template_folder='pycaster/templates')
app.logger = setup_logger(__name__)

@app.before_request
def before_request():
  if not check_trusted_data():
    return "Request Unauthorized", 403

@app.route('/')
def index():
  apps = get_apps()
  app_img_url = url_for('frame_image', app_id=apps[0]['dappId'])
  image_url = f"https://{ app_url }{ app_img_url }"
  post_url = f"https://{ app_url }{ url_for('action', app_id=apps[0]['dappId']) }"
  return render_template('index.html', image_url=image_url, post_url=post_url)

@app.route('/action/<app_id>', methods=['POST'])
def action(app_id: str):
  data = request.get_json(silent=True)
  untrusted_data = data['untrustedData']
  buttonIndex = untrusted_data['buttonIndex']
  if buttonIndex == 1:
    apps = get_apps()
    idx = random.randint(0, len(apps) - 1)
    app_img_url = url_for('frame_image', app_id=apps[idx]['dappId'])
    image_url = f"https://{ app_url }{ app_img_url }"
    post_url = f"https://{ app_url }{ url_for('action', app_id=apps[idx]['dappId']) }"
    return render_template('index.html', image_url=image_url, post_url=post_url)
  elif buttonIndex == 2:
    user_id = f"fc_user:{ untrusted_data['fid'] }"
    redirect_url = f"https://api.meroku.store/api/v1/o/view/{ app_id }?userId={ user_id }"
    return redirect(redirect_url, 302)
  elif buttonIndex == 3:
    image_url = "https://d7aseyv2y654x.cloudfront.net/pycaster-demo/assets/Pre_Rating.png"
    post_url = f"https://{ app_url }{ url_for('rate', app_id=app_id) }"
    return render_template('rate.html', image_url=image_url, post_url=post_url)
  elif buttonIndex == 4:
    redirect_url = f"https://{ app_url }{ url_for('redirect_url', app_id=app_id) }"
    return redirect(redirect_url, 302)

@app.route('/rate/<app_id>', methods=['POST'])
def rate(app_id: str):
  data = request.get_json(silent=True)
  untrusted_data = data['untrustedData']
  buttonIndex = untrusted_data['buttonIndex']
  if buttonIndex == 1:
    rating = 1
  elif buttonIndex == 2:
    rating = 3
  elif buttonIndex == 3:
    rating = 5
  else:
    rating = 3
  rate_app(app_id, rating, untrusted_data['fid'])
  img_url = "https://d7aseyv2y654x.cloudfront.net/pycaster-demo/assets/Ratings_Thanks.png"
  next_url = f"https://{ app_url }{ url_for('thanks', app_id=app_id) }"
  return render_template('thanks.html', image_url=img_url, post_url=next_url)

@app.route('/thanks/<app_id>', methods=['POST'])
def thanks(app_id: str):
  data = request.get_json(silent=True)
  untrusted_data = data['untrustedData']
  buttonIndex = untrusted_data['buttonIndex']
  app.logger.info(f"Button Index: { buttonIndex }")
  try:
    if buttonIndex == 1:
      apps = get_apps()
      idx = random.randint(0, len(apps) - 1)
      app_img_url = url_for('frame_image', app_id=apps[idx]['dappId'])
      image_url = f"https://{ app_url }{ app_img_url }"
      post_url = f"https://{ app_url }{ url_for('action', app_id=apps[idx]['dappId']) }"
      return render_template('index.html', image_url=image_url, post_url=post_url)
    else:
      return redirect("https://dappstore.app", 302)
  except Exception as e:
    app.logger.error(e)
    return redirect("https://dappstore.app", 302)

@app.route('/frame/image/<app_id>')
def frame_image(app_id):
  apps = get_apps()
  apps = filter(lambda x: x['dappId'] == app_id, apps)
  _app = next(apps, None)

  app.logger.info(_app['images'])

  image_stack = []

  app_logo = ImageComponent(
    ImageComponent.EXTERNAL_IMAGE,
    position=(100, 100),
    external_img_url=_app['images']['logo'],
    display_type=ImageComponent.DISPLAY_TYPE_CIRCLE,
    circle_radius=60
  )
  image_stack.append(app_logo)

  app_images = _app['images']
  screenshot_urls = app_images.get('screenshots', [])
  if len(screenshot_urls) == 0:
    screenshot_urls = app_images.get('mobileScreenshots', [])

  # if len(screenshot_urls) > 0:
  #   screenshot_url = screenshot_urls[0]
  #   screenshot = ImageComponent(
  #     ImageComponent.EXTERNAL_IMAGE,
  #     position=(600, 0),
  #     external_img_url=screenshot_url,
  #     display_type=ImageComponent.DISPLAY_TYPE_RECTANGLE,
  #     rect_size=(300, 800)
  #   )
  #   image_stack.append(screenshot)

  app_name = ImageComponent(
    ImageComponent.TEXT,
    position=(120, 0),
    text=_app['name'],
    font_size=40,
    font_color=(128, 128, 128)
  )
  image_stack.append(app_name)

  description = ImageComponent(
    ImageComponent.TEXT,
    position=(0, 200),
    text=_app['description'],
    font_size=30,
    font_color=(0, 0, 0)
  )
  image_stack.append(description)

  img = generate_app_image(image_stack)

  img.seek(0)
  return send_file(img, mimetype='image/png')

@app.route('/redirect/<app_id>')
def redirect_url(app_id: str):
  apps = get_apps()
  apps = filter(lambda x: x['dappId'] == app_id, apps)
  _app = next(apps, None)

  link_url = f"https://explorer.meroku.org/dapp?id={ app_id }"
  cast_text = f"Check out {_app['name']} on Meroku!"
  cast_text = quote(cast_text)
  cast_intent_url = f"https://warpcast.com/~/compose?text={cast_text}&embeds[]={link_url}"
  return redirect(cast_intent_url, 302)
