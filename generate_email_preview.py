from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageOps
from datetime import datetime
import os

OUT_DIR = "screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

LOGO_NAME = 'Cuculus-Logo (1).png'
LOGO_PATH = os.path.join(os.path.dirname(__file__), LOGO_NAME)
OUT_PATH = os.path.join(OUT_DIR, 'email_preview.png')

WIDTH, HEIGHT = 1400, 800

# Prepare background: use a 'contain' layout so the full logo is visible,
# and increase blur so the text reads clearly regardless of logo placement.
if os.path.isfile(LOGO_PATH):
    logo = Image.open(LOGO_PATH).convert('RGBA')
    # Fit the entire logo inside the canvas so the full company name is visible
    # make the logo smaller (50% of canvas) and center it
    contained = ImageOps.contain(logo, (int(WIDTH * 0.5), int(HEIGHT * 0.5)), Image.LANCZOS)
    # Create solid white background and paste the contained logo centered
    bg = Image.new('RGBA', (WIDTH, HEIGHT), (255, 255, 255, 255))
    left = (WIDTH - contained.width) // 2
    # shift logo slightly downward so the watermark sits lower in the frame
    top = (HEIGHT - contained.height) // 2 + int(HEIGHT * 0.06)
    bg.paste(contained, (left, top), contained)
    # Keep a light dim so overlaid text remains readable
    overlay = Image.new('RGBA', (WIDTH, HEIGHT), (255, 255, 255, int(255 * 0.10)))
    bg = Image.alpha_composite(bg, overlay)
else:
    bg = Image.new('RGBA', (WIDTH, HEIGHT), 'white')

# Draw text content inside a translucent card
card_margin = 60
card_w = WIDTH - 2 * card_margin
card_h = 360
card_x = card_margin
card_y = 80

# No white card: draw text directly onto the blurred background
draw = ImageDraw.Draw(bg)

# Fonts
try:
    body_font = ImageFont.truetype('arial.ttf', 20)
except Exception:
    body_font = ImageFont.load_default()

# Text content (matching email)
title_text = 'Hello Team,'
date_text = datetime.now().strftime('%B %d, %Y')
line1 = f'Please find attached the SLA report for the 8-hour profile for Satnam, {date_text}.'
line2 = 'The 8hr LP SLA target has been achieved.'
line3 = 'This is an automated notification from the Cuculus Reporting system.'
line4 = 'Best regards,\nreportbot@CCI'

# Positioning
tx = card_x + 28
ty = card_y + 22

def _text_size(text, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        try:
            return font.getmask(text).size
        except Exception:
            return (100, 20)

# Draw title
def draw_bold_text(draw_obj, position, text, font, fill='#1a1a1a', weight=2):
    x, y = position
    # draw text multiple times with slight offsets to emulate bold
    for ox in range(weight):
        draw_obj.text((x + ox, y), text, fill=fill, font=font)

# Draw 'Hello Team' using the same size as the body text
draw_bold_text(draw, (tx, ty), title_text, body_font, fill='#1a1a1a', weight=2)
# extra spacing after Hello Team
ty += _text_size(title_text, body_font)[1] + 18

# Draw body lines
for ln in [line1, line2, line3]:
    # wrap text if wider than card
    words = ln.split(' ')
    line = ''
    for w in words:
        test = (line + ' ' + w).strip()
        w_width = _text_size(test, body_font)[0]
        if w_width > (card_w - 56):
            if line:
                draw.text((tx, ty), line, fill='#1a1a1a', font=body_font)
                ty += _text_size(line, body_font)[1] + 8
            line = w
        else:
            line = test
    if line:
        # draw body lines in bold (emulated)
        draw_bold_text(draw, (tx, ty), line, body_font, fill='#1a1a1a', weight=1)
        ty += _text_size(line, body_font)[1] + 8

# Draw signature (multiline)
sig_lines = line4.split('\n')
for sl in sig_lines:
    draw_bold_text(draw, (tx, ty), sl, body_font, fill='#1a1a1a', weight=1)
    ty += _text_size(sl, body_font)[1] + 6

OUT_PATH = os.path.join(OUT_DIR, 'email_preview_fullbg.png')
bg.convert('RGB').save(OUT_PATH, quality=95)
print(f'Email preview image saved to: {OUT_PATH}')
