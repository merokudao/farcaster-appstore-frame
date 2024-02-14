import pathlib
from typing import List, Tuple, Union
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pycaster.lib.io import get_external_images

from .utils import setup_logger
from xml.etree.ElementTree import Element, tostring
from xml.dom.minidom import parseString


__current_file_path__ = pathlib.Path(__file__).resolve()
__current_dir__ = __current_file_path__.parent

logger = setup_logger(__name__)

class ImageComponent:
  EXTERNAL_IMAGE = "external"
  TEXT = "text"

  DISPLAY_TYPE_CIRCLE = "circle"
  DISPLAY_TYPE_RECTANGLE = "rectangle"

  def __init__(self,
               component_type: str,
               position: Tuple[int, int],
               external_img_url: Union[str, None] = None,
               display_type: Union[str, None] = None,
               circle_radius = 30,
               text: Union[str, None] = None,
               font_path: Union[str, None] = None,
               font_size = 16,
               font_color = (0, 0, 0),
               rect_size = (100, 100)
               ) -> None:
    self.component_type = component_type
    self.position = position
    self.external_img_url = external_img_url
    self.text = text
    self.display_type = display_type
    self.circle_radius = circle_radius
    self.font_path = font_path
    self.font_size = font_size
    self.font_color = font_color
    self.rect_size = rect_size

def paste_external_image_with_border(
    base_image: Image.Image,
    external_image: Image.Image,
    start_pos: tuple,
    rectangle_dims: tuple,
    border_color: tuple,
    border_radius: int
) -> Image.Image:
    # Calculate the aspect ratio of the external image.
    aspect_ratio = external_image.width / external_image.height
    target_width, target_height = rectangle_dims
    # Resize the external image to fit within the rectangle while maintaining aspect ratio.
    if target_width / target_height > aspect_ratio:
        new_height = target_height
        new_width = int(aspect_ratio * new_height)
    else:
        new_width = target_width
        new_height = int(new_width / aspect_ratio)
    resized_external_image = external_image.resize((new_width, new_height))

    # Create a mask for rounded corners if needed.
    if border_radius > 0:
        mask = Image.new('L', (new_width, new_height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, new_width, new_height),
                               radius=border_radius, fill=255)
        # Apply the mask to give the external image rounded corners.
        rounded_external_image = Image.new('RGBA', (new_width, new_height),
                                           (0, 0, 0, 0))
        rounded_external_image.paste(resized_external_image, (0, 0), mask)
    else:
        rounded_external_image = resized_external_image

    # Create a new image to include the border if needed.
    if border_color and border_radius > 0:
        bordered_image = Image.new('RGBA', (new_width + 2*border_radius,
                                            new_height + 2*border_radius),
                                            border_color)
        bordered_image.paste(rounded_external_image,
                             (border_radius, border_radius), mask=mask)
    else:
        bordered_image = rounded_external_image

    # Paste the external image onto the base image.
    base_image.paste(bordered_image,
                     (start_pos[0], start_pos[1]), bordered_image if border_radius > 0 else None)

    return base_image

def insert_picture_circle(base: Image.Image,
                   profile_img: Image.Image,
                   position,
                   circle_radius=30) -> Image.Image:
    # Ensure the images are in "RGBA" to support transparency
    base = base.convert("RGBA")
    profile_img = profile_img.convert("RGBA")

    # Resize the profile image to a square based on the circle radius
    profile_img = profile_img.resize((circle_radius*2, circle_radius*2))

    # Create a circular mask and apply it to the profile picture
    mask = create_circle_mask((circle_radius*2, circle_radius*2))
    profile_img.putalpha(mask)

    # Adjust the position to be the top-left corner of the circle
    position = (position[0] - circle_radius, position[1] - circle_radius)
    # Paste the profile picture onto the base image at the specified position using the mask for transparency
    base.paste(profile_img, position, mask)

    return base

def write_text_to_image(base: Image, text, position, font_path, font_size) -> Image:
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(font_path, font_size)
    text_width, text_height = textsize(text, font)

    # Adjust the position to center the text
    position = (position[0] - text_width // 2, position[1])

    # Add text onto the image
    draw.text(position, text, font=font, fill=(0, 0, 0))

    return base

def write_multiline_text_to_image(base: Image,
                                  text: str,
                                  position,
                                  font_path,
                                  font_size,
                                  font_color = (0, 0, 0)) -> Image:
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(font_path, font_size)

    # New text width should not fill more than 80% of the image's width
    max_text_width = int(base.size[0] * 0.8)

    # Split the text into words
    words = text.split()
    lines = []
    line = ''

    # Iterate through the words and build lines of text
    for word in words:
        # Check the width of the line with the new word added
        test_line = line + ' ' + word if line else word
        test_line_width, _ = textsize(test_line, font=font)

        # If the test line is too wide, start a new line
        if test_line_width > max_text_width:
            lines.append(line)  # Add the current line to the lines list
            line = word  # Start a new line with the current word
        else:
            line = test_line  # If not too wide, keep adding words to the current line

    # Make sure to add the last line if it exists
    if line:
        lines.append(line)

    # Determine starting position
    y = position[1]

    # Draw the lines on the image
    for line in lines:
        # Recalculate text width for centering each line
        line_width, line_height = textsize(line, font=font)
        # Center the line in the specified position
        line_position = (base.size[0] / 2 - line_width / 2, y)
        # Draw the text
        draw.text(line_position, line, font=font, fill=font_color)
        # Update the y position for the next line
        y += line_height

    # Return the image and the final y-coordinate after the last line of text
    return base, y



# Function to create a circular mask for profile images.
def create_circle_mask(size):
    # Create a new image with a transparent background
    mask = Image.new('L', size, 0)
    # Get drawing context
    draw = ImageDraw.Draw(mask)
    # Draw a filled circle in the center with white (255). This will be the mask.
    draw.ellipse((0, 0) + size, fill=255)
    return mask

def textsize(text, font):
    im = Image.new(mode="P", size=(0, 0))
    draw = ImageDraw.Draw(im)
    _, _, width, height = draw.textbbox((0, 0), text=text, font=font)
    return width, height

def write_text_to_image_right_of_profile(base: Image, text, profile_pos, circle_radius,
                                         font_path, font_size) -> Image:
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(font_path, font_size)
    text_width, text_height = textsize(text, font=font)

    # Position to the right of the profile picture, with some padding
    text_position = (profile_pos[0] + circle_radius * 2 + 10, profile_pos[1] + circle_radius - text_height // 2)

    # Add text onto the image
    draw.text(text_position, text, font=font, fill=(0, 0, 0))

    return base

def insert_profile_picture(base: Image.Image, profile_img: Image.Image,
                           position, circle_radius=30) -> Image.Image:
    # Ensure the images are in "RGBA" to support transparency
    base = base.convert("RGBA")
    profile_img = profile_img.convert("RGBA")

    # Resize the profile image to a square based on the circle radius
    profile_img = profile_img.resize((circle_radius*2, circle_radius*2))

    # Create a circular mask and apply it to the profile picture
    mask = create_circle_mask((circle_radius*2, circle_radius*2))
    profile_img.putalpha(mask)

    # Adjust the position to be the top-left corner of the circle
    position = (position[0] - circle_radius, position[1] - circle_radius)
    # Paste the profile picture onto the base image at the specified position using the mask for transparency
    base.paste(profile_img, position, mask)

    return base

def generate_app_image(components: List[ImageComponent]) -> Image.Image:
  base_image_path = __current_dir__ / "background.png"

  base_image = Image.open(base_image_path.absolute())
  base_width, base_height = base_image.size
  print(base_height, base_width)

  # First fetch any external images in parallel
  external_images = get_external_images(
    [c.external_img_url for c in components if c.component_type == ImageComponent.EXTERNAL_IMAGE]
    )

  for idx, component in enumerate(components):
    if component.component_type == ImageComponent.EXTERNAL_IMAGE and \
      external_images[idx] is not None:
      if component.display_type == ImageComponent.DISPLAY_TYPE_CIRCLE:
        base_image = insert_picture_circle(base_image,
                                          external_images[idx],
                                          component.position,
                                          component.circle_radius)
      elif component.display_type == ImageComponent.DISPLAY_TYPE_RECTANGLE:
        base_image = paste_external_image_with_border(
          base_image,
          external_images[idx],
          component.position,
          component.rect_size,
          (255, 255, 255),
          0
        )
    elif component.component_type == ImageComponent.TEXT and component.text is not None:
      font_path = __current_dir__ / "Inter-Medium.ttf"
      base_image, _ = write_multiline_text_to_image(base_image,
                                      component.text,
                                      component.position,
                                      font_path=font_path,
                                      font_size=component.font_size,
                                      font_color=component.font_color)

  # Return the bytes of base_image
  img_byte_arr = BytesIO()
  base_image.save(img_byte_arr, format='PNG')
  img_byte_arr.seek(0)
  # current_app.logger.debug("Returning image")
  return img_byte_arr


def create_text_svg(text="Hello World\nSecond Line\nThird Line", font_size="16"):
    view_box_width = 191*3
    view_box_height = 100*3
    svg = Element('svg', viewBox=f"0 0 {view_box_width} {view_box_height}", version='1.1', xmlns='http://www.w3.org/2000/svg', style="background: white;")
    style = Element('style')
    # Basic style for text elements
    style.text = f"""
    text {{ font-family: 'Arial', sans-serif; font-size: {font_size}px; fill: black; }}
    """
    svg.append(style)

    sentences = text.split('\n')
    assert len(sentences) <= 3, "There should be no more than 3 sentences."

    words_per_line = max(1, view_box_width // (int(font_size) * 4))
    line_height = int(font_size) * 1.5
    vertical_positions = [0.25, 0.5, 0.75]  # Top, middle, bottom positions in terms of height fraction

    for i, sentence in enumerate(sentences):
        words = sentence.split(' ')
        current_line_height = view_box_height * vertical_positions[i] - (line_height if i == 2 else line_height / 2)

        for j in range(0, len(words), words_per_line):
            line_text = ' '.join(words[j:j+words_per_line])
            text_element = Element('text', y=str(int(current_line_height + line_height * (j // words_per_line))))
            text_element.set('style', f"white-space: pre; font-size: {font_size}px;")

            if i == 0:  # Center align first sentence, make it bold
                text_element.set('x', '50%')
                text_element.set('text-anchor', 'middle')
                text_element.set('style', text_element.get('style') + " font-weight: bold;")
            elif i == 1:  # Center align second sentence
                text_element.set('x', '50%')
                text_element.set('text-anchor', 'middle')
            elif i == 2:  # Right align third sentence, make it italic
                text_element.set('x', '80%')
                text_element.set('text-anchor', 'end')
                text_element.set('style', text_element.get('style') + " font-style: italic;")

            text_element.text = line_text
            svg.append(text_element)

    return parseString(tostring(svg)).toprettyxml(indent="  ")
