import streamlit as st
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import base64
import traceback

from google import genai
from google.genai import types
from streamlit_image_coordinates import streamlit_image_coordinates

# ==================================================
# PAGE CONFIG (MUST BE FIRST)
# ==================================================
st.set_page_config(
    page_title="SRS – Strict Replication Try-On",
    page_icon="👗",
    layout="wide"
)

# ==================================================
# GEMINI CONFIG
# ==================================================
GEMINI_API_KEY = st.secrets.get("SRS_KEY")
if not GEMINI_API_KEY:
    st.error("❌ SRS_KEY missing in Streamlit secrets.")
    st.stop()

MODEL_NAME = "gemini-3-pro-image-preview"

# ==================================================
# IMAGE UTILS
# ==================================================
def image_size_mb(img: Image.Image) -> float:
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return round(buf.tell() / (1024 * 1024), 2)

def compress_upload_image(img: Image.Image, upload_quality: int) -> Image.Image:
    img = img.convert("RGB")

    MAX_DIM = 2048
    w, h = img.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    TARGET_MIN = 1 * 1024 * 1024
    TARGET_MAX = 2 * 1024 * 1024

    quality = upload_quality
    last_buf = None

    while quality >= 55:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        size = buf.tell()
        last_buf = buf

        if TARGET_MIN <= size <= TARGET_MAX:
            buf.seek(0)
            return Image.open(buf)

        quality -= 3

    last_buf.seek(0)
    return Image.open(last_buf)

def pil_image_to_part(img: Image.Image):
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part.from_bytes(
        data=buf.getvalue(),
        mime_type="image/png"
    )

# ==================================================
# GEMINI RESPONSE SAFETY
# ==================================================
def extract_image_safe(resp):
    for cand in getattr(resp, "candidates", []):
        if not cand.content:
            continue
        for part in cand.content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.mime_type and inline.mime_type.startswith("image/"):
                data = inline.data
                return base64.b64decode(data) if isinstance(data, str) else data
    return None

def safe_open_image(img_bytes):
    try:
        img = Image.open(BytesIO(img_bytes))
        img.verify()
        return Image.open(BytesIO(img_bytes))
    except (UnidentifiedImageError, Exception):
        return None

# ==================================================
# PROMPTS
# ==================================================
VIRTUAL_TRYON_PROMPT = """
Generate a photorealistic image of a professional Indian fashion model wearing this EXACT lehenga outfit.

FORBIDDEN ACTIONS:
- Do NOT redesign
- Do NOT beautify
- Do NOT correct symmetry
- Do NOT enhance embroidery
- Do NOT hallucinate missing details

LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Baju / Sleeve
- Blouse Border
- Upper Waist Seam

ABSOLUTE CONSTRAINTS:
- Pixel-adjacent replication only
- Background must NOT affect garment colors or shape
"""

DRESS_BACKGROUND_MAP = {
    "Printed Lehenga": "BACKGROUND: Plain simple background.",
    "Fusion Dress": "BACKGROUND: Plain simple background.",
    "Heavy Lehenga": "BACKGROUND: Royal outdoor background.",
    "Indo-Western": "BACKGROUND: Royal outdoor background.",
    "Gown": "BACKGROUND: Elegant outdoor background."
}

POSE_PROMPTS = {
    "Natural Standing": "POSE: Natural upright standing pose.",
    "Soft Fashion": "POSE: Slight hip shift, relaxed arms.",
    "Editorial": "POSE: Editorial fashion pose.",
    "Walk": "POSE: Mild walking stance."
}

# ==================================================
# UI
# ==================================================
st.title("👗 SRS – Strict Replication Try-On")

with st.sidebar:
    st.header("⚙️ Settings")

    upload_quality = st.slider(
        "Upload Image Quality",
        60, 95, 85,
        help="Controls compression of uploaded images ONLY (1–2 MB enforced)"
    )

    generation_resolution = st.selectbox(
        "Generation Resolution",
        ["1K", "2K", "4K"],
        index=1
    )

    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        ["1:1", "2:3", "3:4", "4:5", "9:16"],
        index=2
    )

    dress_type = st.selectbox("Dress Type", list(DRESS_BACKGROUND_MAP.keys()))
    pose_style = st.selectbox("Pose Style", list(POSE_PROMPTS.keys()))
    color_mode = st.selectbox("Color Mode", ["Automatic", "Manual (Dropper)"])

# ==================================================
# IMAGE UPLOADS
# ==================================================
col1, col2 = st.columns(2)

with col1:
    main_file = st.file_uploader("Upload Main Image", ["jpg", "jpeg", "png"])
    main_image = None

    if main_file:
        raw = Image.open(main_file)
        original_size = round(main_file.size / (1024 * 1024), 2)
        main_image = compress_upload_image(raw, upload_quality)
        compressed_size = image_size_mb(main_image)

        st.image(main_image, width='stretch')
        st.caption(
            f"📦 Original: {original_size} MB → "
            f"Compressed: {compressed_size} MB "
            f"{'✅' if 1 <= compressed_size <= 2 else '⚠️'}"
        )

with col2:
    ref1_file = st.file_uploader("Upload Choli Reference", ["jpg", "jpeg", "png"])
    ref2_file = st.file_uploader("Upload Lehenga Reference", ["jpg", "jpeg", "png"])

    ref1_image = compress_upload_image(Image.open(ref1_file), upload_quality) if ref1_file else None
    ref2_image = compress_upload_image(Image.open(ref2_file), upload_quality) if ref2_file else None

# ==================================================
# COLOR PICKER (FIXED + VISIBLE)
# ==================================================
blouse_color = lehenga_color = dupatta_color = "#FFFFFF"

if color_mode == "Manual (Dropper)" and main_image:
    st.subheader("🎯 Manual Color Picker")

    preview = main_image.resize((300, 300))
    coords = streamlit_image_coordinates(preview, key="color_picker")

    if coords:
        px, py = coords["x"], coords["y"]
        ow, oh = main_image.size
        rx, ry = int(px * ow / 300), int(py * oh / 300)

        r, g, b = main_image.getpixel((rx, ry))
        picked_hex = f"#{r:02x}{g:02x}{b:02x}"

        target = st.selectbox(
            "Apply picked color to",
            ["Blouse", "Lehenga", "Dupatta"],
            key="color_target"
        )

        if target == "Blouse":
            blouse_color = picked_hex
        elif target == "Lehenga":
            lehenga_color = picked_hex
        else:
            dupatta_color = picked_hex

        st.markdown(
            f"""
            <div style="
                width:80px;
                height:80px;
                background:{picked_hex};
                border-radius:8px;
                border:2px solid black;
                margin-top:10px;
            "></div>
            <b>Selected:</b> {picked_hex}
            """,
            unsafe_allow_html=True
        )

# ==================================================
# GENERATION WITH FALLBACK
# ==================================================
def generate_with_fallback(client, parts, aspect_ratio, resolution):
    order = [resolution]
    if resolution == "4K":
        order += ["2K", "1K"]
    elif resolution == "2K":
        order += ["1K"]

    for res in order:
        try:
            return client.models.generate_content(
                model=MODEL_NAME,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=res
                    )
                )
            )
        except Exception:
            continue
    return None

# ==================================================
# GENERATE BUTTON
# ==================================================
if st.button("🎨 Generate Image"):
    if not main_image:
        st.error("Please upload a main image.")
        st.stop()

    with st.spinner("🎨 Generating image… Please wait"):
        try:
            final_prompt = (
                VIRTUAL_TRYON_PROMPT
                + f"""

HIGH-PRIORITY COLOR LOCK (MANDATORY):
The following colors are USER-SELECTED and MUST be applied EXACTLY.
These instructions OVERRIDE any automatic color inference.

Blouse Color (LOCKED): {blouse_color}
Lehenga Color (LOCKED): {lehenga_color}
Dupatta Color (LOCKED): {dupatta_color}

COLOR ENFORCEMENT:
- Manual colors have higher priority
- Do not shift hue, saturation, or brightness
"""
                + DRESS_BACKGROUND_MAP[dress_type]
                + POSE_PROMPTS[pose_style]
            )

            parts = [
                types.Part.from_text(text=final_prompt),
                pil_image_to_part(main_image)
            ]

            if ref1_image:
                parts.append(pil_image_to_part(ref1_image))
            if ref2_image:
                parts.append(pil_image_to_part(ref2_image))

            client = genai.Client(api_key=GEMINI_API_KEY)

            response = generate_with_fallback(
                client,
                parts,
                aspect_ratio,
                generation_resolution
            )

            if response is None:
                st.error("Gemini failed internally. Try lower resolution.")
                st.stop()

            img_bytes = extract_image_safe(response)
            if img_bytes is None:
                st.error("Gemini response contained no image.")
                st.stop()

            out_img = safe_open_image(img_bytes)
            if out_img is None:
                st.error("Returned content is not a valid image.")
                st.stop()

            st.image(out_img, width='stretch')

            buf = BytesIO()
            out_img.save(buf, format="JPEG", quality=95)
            st.download_button(
                "📥 Download Image",
                buf.getvalue(),
                "srs_output.jpg",
                "image/jpeg"
            )

        except Exception:
            st.error("❌ Generation failed.")
            st.text(traceback.format_exc())
