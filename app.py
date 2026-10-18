import io
import os
import zipfile

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

st.set_page_config(page_title="Ticket Image Editor", page_icon="🎟️", layout="centered")

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.png")
# Bundle the font with the project so local Windows and Streamlit Cloud use
# the same font file instead of falling back to Pillow's tiny default font.
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "arialbd.ttf")

# Authorized blank-template configuration. Coordinates are pixel positions in
# the supplied 1600 x 624 image and should be adjusted for another template.
EDITABLE_FIELDS = {
    "date": {"box": (620, 543, 980, 584), "font_file": FONT_PATH, "font_size": 44, "text_color": (255, 255, 255), "max_width": 330, "padding": 8, "horizontal": "center", "vertical": "center"},
    "price": {"box": (724, 18, 1111, 113), "font_file": FONT_PATH, "font_size": 88, "text_color": (24, 40, 45), "max_width": 365, "padding": 8, "horizontal": "center", "vertical": "center"},
    "ticket_number": {"box": (1242, 96, 1518, 158), "font_file": FONT_PATH, "font_size": 50, "text_color": (24, 40, 45), "max_width": 255, "padding": 8, "horizontal": "center", "vertical": "center"},
}

def get_font(size, font_file=None, bold=True):
    candidates = [
        font_file,
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if not path:
            continue
        try:
            if not os.path.exists(path):
                continue
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()

def fit_font(draw, text, max_width, start_size, font_file=None):
    for size in range(start_size, 9, -1):
        font = get_font(size, font_file)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
    return get_font(10, font_file)


def reconstruct_background(image, box):
    """Remove old lettering with edge-aware inpainting inside one field only.

    OpenCV's Telea inpainting uses nearby pixels and follows the local colour
    gradients. This avoids the dark streaks produced when text pixels at a box
    edge are copied across the whole field.
    """
    if cv2 is None or np is None:
        # Pillow-only fallback: use a lightly blurred crop of the surrounding
        # area rather than copying potentially dark text edge pixels.
        from PIL import ImageFilter
        left, top, right, bottom = box
        crop = image.crop((max(0, left - 4), max(0, top - 4), min(image.width, right + 5), min(image.height, bottom + 5)))
        image.paste(crop.filter(ImageFilter.GaussianBlur(2)).crop((4, 4, 4 + right - left + 1, 4 + bottom - top + 1)), (left, top))
        return

    pixels = np.array(image)
    mask = np.zeros((image.height, image.width), dtype=np.uint8)
    left, top, right, bottom = box
    mask[max(0, top):min(image.height, bottom + 1), max(0, left):min(image.width, right + 1)] = 255
    repaired = cv2.inpaint(cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR), mask, 5, cv2.INPAINT_TELEA)
    image.paste(Image.fromarray(cv2.cvtColor(repaired, cv2.COLOR_BGR2RGB)), (0, 0))

def draw_centered(draw, box, text, font, fill, horizontal="center", vertical="center"):
    left, top, right, bottom = box
    bounds = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    x = left if horizontal == "left" else right - text_width if horizontal == "right" else left + (right - left - text_width) // 2
    y = top if vertical == "top" else bottom - text_height if vertical == "bottom" else top + (bottom - top - text_height) // 2
    x -= bounds[0]
    y -= bounds[1]
    draw.text((x, y), text, font=font, fill=fill)


def render_ticket(date_text, price_text, ticket_number):
    """Clean each designated area, then draw the replacement value."""
    with Image.open(TEMPLATE_PATH) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    for name, value in {"date": date_text, "price": price_text, "ticket_number": ticket_number}.items():
        field = EDITABLE_FIELDS[name]
        # The supplied master is already blank in these fields, so do not
        # touch its pixels before rendering. This preserves the original
        # gradients and decorative artwork exactly.
        available_width = max(1, field["max_width"] - (2 * field.get("padding", 0)))
        font = fit_font(draw, value, available_width, field["font_size"], field["font_file"])
        draw_centered(draw, field["box"], value, font, field["text_color"], field["horizontal"], field["vertical"])
    return image


def export_bytes(image, format_name):
    buffer = io.BytesIO()
    if format_name == "JPEG":
        image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=95, optimize=True)
    else:
        image.save(buffer, format="PNG")
    return buffer.getvalue()


def create_cart_zip(images):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for index, image in enumerate(images, start=1):
            bundle.writestr(f"ticket_{index:03d}.jpg", export_bytes(image, "JPEG"))
    return archive.getvalue()


def reset_editor():
    for key in ("date_input", "price_input", "number_input", "ticket_image", "cart_images", "show_cart_downloads"):
        st.session_state.pop(key, None)


st.markdown("""
<style>
    .block-container { max-width: 1100px; padding: 1rem 1rem 2rem; }
    .stButton > button, .stDownloadButton > button, div[data-testid="stFormSubmitButton"] button {
        background: #f7f7f5; color: #111827; border: 1px solid #b7bcc5;
        border-radius: 8px; font-weight: 600; min-height: 2.7rem;
    }
    .stButton > button:hover, .stDownloadButton > button:hover,
    div[data-testid="stFormSubmitButton"] button:hover { background: #e5e7eb; color: #000; border-color: #6b7280; }
    [data-testid="stMetric"] { background: transparent; border: 0; box-shadow: none; padding: .15rem 0; }
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color: #f7f7f5 !important; }
    @media (max-width: 640px) {
        .block-container { padding: .75rem .6rem 1.25rem; }
        h1 { font-size: 1.55rem !important; }
        div[data-testid="stDownloadButton"] button,
        div[data-testid="stFormSubmitButton"] button { min-height: 2.8rem; }
    }
</style>
""", unsafe_allow_html=True)
st.title("Ticket Image Editor")

if not os.path.exists(TEMPLATE_PATH):
    st.error("The template.png file is missing from the project directory.")
    st.stop()

with st.form("editor"):
    date_text = st.text_input("Date", placeholder="DD-MM-YYYY", max_chars=30, key="date_input")
    price_text = st.text_input("Ticket Price", placeholder="₹50", max_chars=30, key="price_input")
    ticket_number = st.text_input("Ticket Number", max_chars=40, key="number_input")
    submitted = st.form_submit_button("Generate Preview", use_container_width=True)

if submitted:
    date_value = date_text.strip()
    price_value = price_text.strip()
    number_value = ticket_number.strip().upper()
    if price_value and not price_value.startswith("₹"):
        price_value = "₹" + price_value
    values = [date_value, price_value, number_value]
    if not all(values):
        st.error("Please enter a Date, Ticket Price, and Ticket Number.")
    else:
        st.session_state.ticket_image = render_ticket(*values)

if "ticket_image" in st.session_state:
    result = st.session_state.ticket_image
    st.image(result, use_container_width=True)
    if "cart_images" not in st.session_state:
        st.session_state.cart_images = []

    current_download, cart_add = st.columns(2)
    with current_download:
        st.download_button(
            "Download JPEG",
            export_bytes(result, "JPEG"),
            "ticket.jpeg",
            "image/jpeg",
            use_container_width=True,
        )
    with cart_add:
        if st.button("Add current image to cart", use_container_width=True):
            st.session_state.cart_images.append(result.copy())
            st.success(f"Added to cart. Cart count: {len(st.session_state.cart_images)}")

    st.metric("Cart images", len(st.session_state.cart_images))
    if st.session_state.cart_images:
        download_cart, reset_cart = st.columns(2)
        with download_cart:
            st.download_button("Download cart", data=create_cart_zip(st.session_state.cart_images), file_name="tickets_cart.zip", mime="application/zip", use_container_width=True)
        with reset_cart:
            st.button("Reset cart and inputs", on_click=reset_editor, use_container_width=True)
