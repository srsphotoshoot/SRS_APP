import streamlit as st
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import base64
import traceback

from google import genai
from google.genai import types
from streamlit_image_coordinates import streamlit_image_coordinates

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="SRS – Strict Replication Try-On",
    page_icon="👗",
    layout="wide"
)

# ==================================================
# GEMINI CONFIG
# ==================================================
GEMINI_API_KEY = st.secrets.get("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    st.error("❌ GOOGLE_API_KEY missing in Streamlit secrets.")
    st.stop()

MODEL_NAME = "gemini-3-pro-image-preview"

# ==================================================
# SESSION STATE
# ==================================================
st.session_state.setdefault("last_generated_image", None)
st.session_state.setdefault("retry_mode", False)
st.session_state.setdefault("final_prompt", "")

# ==================================================
# IMAGE UTILS
# ==================================================
def image_size_mb(img):
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return round(buf.tell() / (1024 * 1024), 2)

def compress_upload_image(img, upload_quality):
    img = img.convert("RGB")

    MAX_DIM = 2048
    w, h = img.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    quality = upload_quality
    last_buf = None

    while quality >= 55:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        last_buf = buf
        size = buf.tell()
        if 1 * 1024 * 1024 <= size <= 2 * 1024 * 1024:
            buf.seek(0)
            return Image.open(buf)
        quality -= 3

    last_buf.seek(0)
    return Image.open(last_buf)

def pil_image_to_part(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part.from_bytes(
        data=buf.getvalue(),
        mime_type="image/png"
    )

# ==================================================
# GEMINI SAFETY
# ==================================================
def extract_image_safe(resp):
    for cand in getattr(resp, "candidates", []):
        if not cand.content:
            continue
        for part in cand.content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.mime_type.startswith("image/"):
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
# GARMENT-AWARE PROMPTS
# ==================================================
BASE_PROMPT_MAP = {
    "Printed Lehenga": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT LEHENGA outfit.",
    "Heavy Lehenga": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT LEHENGA outfit.",
    "Fusion Dress": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT FUSION outfit.",
    "Indo-Western": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT INDO-WESTERN outfit.",
    "Gown": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT GOWN."
}

LOCKED_REGION_MAP = {
    "Printed Lehenga": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Baju / Sleeve
- Blouse Border
- Upper Waist Seam
""",
    "Heavy Lehenga": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Baju / Sleeve
- Blouse Border
- Upper Waist Seam
""",
    "Fusion Dress": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Sleeve ends
- Top-to-bottom transition seam
""",
    "Indo-Western": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Sleeve ends
- Top-to-bottom transition seam
""",
    "Gown": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Bodice seam
- Waist transition (if present)
"""
}

DUPATTA_LOCK_PROMPT = """
CRITICAL DUPATTA ENFORCEMENT (HIGHEST PRIORITY):
- Dupatta width MUST remain unchanged
- Border thickness MUST remain identical
- Embroidery scale MUST NOT change
- Motif spacing MUST NOT change
- Thread density MUST match reference
FAIL THE IMAGE IF DUPATTA DIFFERS.
"""

def get_dupatta_prompt(dress_type):
    if dress_type in ["Printed Lehenga", "Heavy Lehenga", "Fusion Dress"]:
        return DUPATTA_LOCK_PROMPT
    return ""

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
# FINAL PROMPT BUILDER
# ==================================================
def build_final_prompt(dress_type, blouse_color, lehenga_color, dupatta_color, pose_style):
    return (
        BASE_PROMPT_MAP[dress_type]
        + "\n\nFORBIDDEN ACTIONS:\n"
          "- Do NOT redesign\n"
          "- Do NOT beautify\n"
          "- Do NOT correct symmetry\n"
          "- Do NOT enhance embroidery\n"
          "- Do NOT hallucinate missing details\n"
        + LOCKED_REGION_MAP[dress_type]
        + get_dupatta_prompt(dress_type)
        + """
GARMENT CLASS LOCK (ABSOLUTE):
- DO NOT reinterpret gowns or indo-western outfits as lehengas
- DO NOT add dupatta unless present in reference
"""
        + f"""
HIGH-PRIORITY COLOR LOCK (HEX):
Blouse: {blouse_color}
Lehenga: {lehenga_color}
Dupatta: {dupatta_color}
"""
        + "\nABSOLUTE CONSTRAINTS:\n"
          "- Pixel-adjacent replication only\n"
          "- Background must NOT affect garment colors or shape\n"
        + "\n"
        + DRESS_BACKGROUND_MAP[dress_type]
        + "\n"
        + POSE_PROMPTS[pose_style]
    )

# ==================================================
# UI
# ==================================================
st.title("👗 SRS – Strict Replication Try-On")

with st.sidebar:
    upload_quality = st.slider("Upload Image Quality", 60, 95, 85)
    generation_resolution = st.selectbox("Generation Resolution", ["1K", "2K", "4K"], index=1)
    aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "2:3", "3:4", "4:5", "9:16"], index=2)
    dress_type = st.selectbox("Dress Type", list(DRESS_BACKGROUND_MAP.keys()))
    pose_style = st.selectbox("Pose Style", list(POSE_PROMPTS.keys()))
    color_mode = st.selectbox("Color Mode", ["Automatic", "Manual (Dropper)"])

# ==================================================
# IMAGE INPUTS
# ==================================================
col1, col2 = st.columns(2)

with col1:
    main_file = st.file_uploader("Upload Main Image", ["jpg", "jpeg", "png"])
    main_image = compress_upload_image(Image.open(main_file), upload_quality) if main_file else None
    if main_image:
        st.image(main_image, width="stretch")

with col2:
    ref1_file = st.file_uploader("Upload Choli Reference", ["jpg", "jpeg", "png"])
    ref2_file = st.file_uploader("Upload Lehenga Reference", ["jpg", "jpeg", "png"])
    ref1_image = compress_upload_image(Image.open(ref1_file), upload_quality) if ref1_file else None
    ref2_image = compress_upload_image(Image.open(ref2_file), upload_quality) if ref2_file else None

# ==================================================
# COLOR PICKER (PIXEL-ACCURATE)
# ==================================================
blouse_color = lehenga_color = dupatta_color = "#FFFFFF"

if color_mode == "Manual (Dropper)" and main_image:
    st.subheader("🎯 Manual Color Picker")
    coords = streamlit_image_coordinates(main_image, key="picker", use_column_width=True)
    if coords:
        disp_x, disp_y = int(coords["x"]), int(coords["y"])
        disp_w, disp_h = int(coords["width"]), int(coords["height"])
        orig_w, orig_h = main_image.size

        real_x = int(disp_x * orig_w / disp_w)
        real_y = int(disp_y * orig_h / disp_h)

        real_x = max(0, min(real_x, orig_w - 1))
        real_y = max(0, min(real_y, orig_h - 1))

        r, g, b = main_image.getpixel((real_x, real_y))
        picked_hex = f"#{r:02X}{g:02X}{b:02X}"

        target = st.selectbox("Apply picked color to", ["Blouse", "Lehenga", "Dupatta"])
        if target == "Blouse":
            blouse_color = picked_hex
        elif target == "Lehenga":
            lehenga_color = picked_hex
        else:
            dupatta_color = picked_hex

# ==================================================
# FALLBACK GENERATION
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
# GENERATE
# ==================================================
if st.button("🎨 Generate Image") and main_image:
    with st.spinner("Generating image..."):
        try:
            st.session_state.final_prompt = build_final_prompt(
                dress_type, blouse_color, lehenga_color, dupatta_color, pose_style
            )

            parts = [
                types.Part.from_text(text=st.session_state.final_prompt),
                pil_image_to_part(main_image)
            ]
            if ref1_image:
                parts.append(pil_image_to_part(ref1_image))
            if ref2_image:
                parts.append(pil_image_to_part(ref2_image))

            response = generate_with_fallback(
                genai.Client(api_key=GEMINI_API_KEY),
                parts,
                aspect_ratio,
                generation_resolution
            )

            img_bytes = extract_image_safe(response)
            out_img = safe_open_image(img_bytes)
            if not out_img:
                st.error("Invalid image returned.")
                st.stop()

            st.image(out_img, width="stretch")

            # ✅ DOWNLOAD BUTTON (FIRST GENERATION)
            buf = BytesIO()
            out_img.save(buf, format="JPEG", quality=95)
            st.download_button(
                "⬇️ Download First Output",
                buf.getvalue(),
                "srs_output_v1.jpg",
                "image/jpeg"
            )

            st.session_state.last_generated_image = out_img
            st.session_state.retry_mode = True

        except Exception:
            st.error("❌ Generation failed.")
            st.text(traceback.format_exc())

# ==================================================
# DELTA FIX
# ==================================================
if st.session_state.retry_mode and st.session_state.last_generated_image and main_image:
    st.divider()
    delta = st.text_area("Describe ONLY what is wrong")

    if st.button("♻️ Fix & Regenerate"):
        with st.spinner("Re-generating image..."):
            try:
                parts = [
                    types.Part.from_text(text=st.session_state.final_prompt + f"\nONLY FIX:\n{delta}"),
                    pil_image_to_part(main_image),
                    pil_image_to_part(st.session_state.last_generated_image)
                ]
                if ref1_image:
                    parts.append(pil_image_to_part(ref1_image))
                if ref2_image:
                    parts.append(pil_image_to_part(ref2_image))

                response = generate_with_fallback(
                    genai.Client(api_key=GEMINI_API_KEY),
                    parts,
                    aspect_ratio,
                    generation_resolution
                )

                img_bytes = extract_image_safe(response)
                out_img = safe_open_image(img_bytes)
                if out_img:
                    st.image(out_img, width="stretch")

                    # ✅ DOWNLOAD BUTTON (SECOND GENERATION)
                    buf = BytesIO()
                    out_img.save(buf, format="JPEG", quality=95)
                    st.download_button(
                        "⬇️ Download Fixed Output",
                        buf.getvalue(),
                        "srs_output_v2_fixed.jpg",
                        "image/jpeg"
                    )

                    st.session_state.last_generated_image = out_img

            except Exception:
                st.error("❌ Regeneration failed.")
                st.text(traceback.format_exc())
