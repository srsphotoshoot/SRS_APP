import streamlit as st
from PIL import Image
from io import BytesIO
import base64
import json
import traceback
import numpy as np

from google import genai
from google.genai import types
################################
# working well accuracy ~ 85% 
################################
# ready to deploy
################################
from streamlit_image_coordinates import streamlit_image_coordinates


# -----------------------
# Config / Keysf
# -----------------------
GEMINI_API_KEY = st.secrets.get("GOOGLE_API_KEY")
FLASH_API_KEY = st.secrets.get("GOOGLE_API_KEY_FLASH", GEMINI_API_KEY)

if not GEMINI_API_KEY:
    st.error("API key missing in Streamlit secrets (GOOGLE_API_KEY).")
    st.stop()

MODEL_NAME = "gemini-3-pro-image-preview"
FLASH_MODEL = "gemini-1.5-flash"

RESOLUTION_MAP = {"1K": 1024, "2K": 2048, "4K": 4096}

# -----------------------
# PROMPT
# -----------------------
VIRTUAL_TRYON_PROMPT = """
Generate a photorealistic image of a professional Indian fashion model wearing this EXACT lehenga outfit.

STRICTLY DO NOT MAKE ANY CHANGE IN DRESS.

LEHENGA & DUPATTA ACCURACY
• Replicate lehenga silhouette, flare volume, kalis/panels, pleats, hemline width, embroidery layout, and waistband design.
• Match skirt flow, fold depth, and fabric weight exactly.
• Dupatta must retain original drape style, border design, booti work, transparency level, and fall direction.
• Preserve exact border width, embellishment type, and corner tassels/latkans.
• do not add any kind of extra objects in dupatta replicate only those who are in refrence images.

SHINE, SPARKLE & DETAILS
• Preserve shimmer/sparkle effects, metallic highlights, crystal reflections, and stone glints exactly as captured in the reference.
• Maintain natural shadowing from folds and borders; do not alter shadow placement.
ABSOLUTE CONSTRAINTS:
- Do not modify embroidery geometry
- Do not smooth borders
- Do not interpolate missing patterns
- Pixel-adjacent replication only

"""

st.set_page_config(page_title="SHREE RADHA STUDIO TRY-ON", page_icon="👗", layout="wide")
st.title("SRS-TRY-ON")


# ================================
# SIDEBAR
# ================================
with st.sidebar:
    st.header("⚙️ Settings")

    resolution_choice = st.selectbox("Resolution", ["1K", "2K", "4K"], index=1)

    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"],
        index=3
    )

    st.subheader("🎨 Color Mode")
    color_mode = st.selectbox(
        "Choose Mode",
        ["Automatic Color Detection (Recommended)", "Manual 3-Color Override (Dropper)"]
    )

    blouse_color = "#FFFFFF"
    lehenga_color = "#FFFFFF"
    dupatta_color = "#FFFFFF"


# ================================
# IMAGE UPLOAD SECTION
# ================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📤 Upload Main Lehenga Image")
    main_image_file = st.file_uploader("Main Image", type=["jpg", "jpeg", "png"])
    main_image = None

    if main_image_file:
        main_image = Image.open(main_image_file).convert("RGB")
        st.image(main_image, caption="Main Dress Image", use_container_width=True)

with col2:
    st.subheader("📤 CHOLI / UPPER IMAGE")
    ref1_file = st.file_uploader("CHOLI/UPPER IMAGE", type=["jpg", "jpeg", "png"])
    ref1_image = Image.open(ref1_file).convert("RGB") if ref1_file else None

    st.subheader("📤 LEHENGA/MAIN IMAGE")
    ref2_file = st.file_uploader("LEHENGA/MAIN IMAGE", type=["jpg", "jpeg", "png"])
    ref2_image = Image.open(ref2_file).convert("RGB") if ref2_file else None


# ================================
# 300×300 MINI COLOR PICKER
# ================================
if color_mode == "Manual 3-Color Override (Dropper)" and main_image:

    st.subheader("🎯 Mini 300×300 Color Picker (Extracts Full-Res Color)")

    # Create 300×300 thumbnail preview
    pick_view = main_image.resize((300, 300))

    coords = streamlit_image_coordinates(pick_view, key="mini_picker")

    if coords:
        px, py = coords["x"], coords["y"]

        # Map back to original image coordinates
        orig_w, orig_h = main_image.size
        scale_x = orig_w / 300
        scale_y = orig_h / 300

        real_x = int(px * scale_x)
        real_y = int(py * scale_y)

        # Pick color from full resolution
        r, g, b = main_image.getpixel((real_x, real_y))
        picked_hex = '#%02x%02x%02x' % (r, g, b)

        st.success(f"Picked Color 👉 RGB({r},{g},{b}) → {picked_hex}")

        st.markdown(
            f"""
            <div style="width:80px;height:80px;background:{picked_hex};
            border-radius:10px;border:2px solid black;"></div>
            """,
            unsafe_allow_html=True
        )

        choice = st.selectbox(
            "Assign Picked Color To:",
            ["Blouse", "Lehenga", "Dupatta"]
        )

        if choice == "Blouse":
            blouse_color = picked_hex
        elif choice == "Lehenga":
            lehenga_color = picked_hex
        else:
            dupatta_color = picked_hex


generate_btn = st.button("🎨 Generate Model Image")


# ================================
# HELPERS (unchanged)
# ================================
def image_to_part(pil_image: Image.Image) -> types.Part:
    buf = BytesIO()
    pil_image.save(buf, format="PNG")
    data = buf.getvalue()
    return types.Part.from_bytes(data=data, mime_type="image/png")


def extract_text_from_response(resp):
    try:
        if hasattr(resp, "candidates") and resp.candidates:
            texts = []
            for cand in resp.candidates:
                if hasattr(cand, "content") and getattr(cand.content, "parts", None):
                    for p in cand.content.parts:
                        if getattr(p, "text", None):
                            texts.append(p.text)
                if getattr(cand, "text", None):
                    texts.append(cand.text)
            return "\n".join(texts).strip()
        if getattr(resp, "text", None):
            return resp.text.strip()
        return str(resp)
    except:
        return str(resp)


def extract_image_bytes_from_response(resp):
    try:
        if hasattr(resp, "candidates") and resp.candidates:
            cand = resp.candidates[0]
            if hasattr(cand, "content") and getattr(cand.content, "parts", None):
                for part in cand.content.parts:
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        data = inline.data
                        if isinstance(data, (bytes, bytearray)):
                            return bytes(data)
                        if isinstance(data, str):
                            return base64.b64decode(data)
        return None
    except:
        return None


# ================================
# MAIN GENERATION LOGIC
# ================================
if generate_btn:
    if not main_image:
        st.error("Please upload the main image.")
        st.stop()

    with st.spinner("Generating model image… ⏳"):

        try:
            image_size = RESOLUTION_MAP.get(resolution_choice, 2048)

            # MANUAL MODE ONLY — USE PICKED COLORS
            color_prompt = f"""
MANUAL COLORS (Pick-Dropper):
Blouse Color  : {blouse_color}
Lehenga Color : {lehenga_color}
Dupatta Color : {dupatta_color}
"""

            final_prompt = VIRTUAL_TRYON_PROMPT + "\n" + color_prompt

            parts = [types.Part.from_text(text=final_prompt), image_to_part(main_image)]
            if ref1_image: parts.append(image_to_part(ref1_image))
            if ref2_image: parts.append(image_to_part(ref2_image))

            content = types.Content(role="user", parts=parts)

            client = genai.Client(api_key=GEMINI_API_KEY)

            config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution_choice
                )
            )

            response = client.models.generate_content(
                model=MODEL_NAME, contents=[content], config=config
            )

            output_image_data = extract_image_bytes_from_response(response)
            description_text = extract_text_from_response(response)

            if output_image_data:
                generated_image = Image.open(BytesIO(output_image_data)).convert("RGB")
                st.image(generated_image, caption="Generated Output", use_container_width=True)

                buf = BytesIO()
                generated_image.save(buf, format="JPEG", quality=95)
                st.download_button("📥 Download Image", buf.getvalue(), "output.jpg", "image/jpeg")

                if description_text:
                    with st.expander("📄 Description"):
                        st.write(description_text)

            else:
                st.error("Could not extract generated image.")
                st.write(response)

        except Exception as e:
            st.error(str(e))
            st.text(traceback.format_exc())
