import streamlit as st
from PIL import Image
from io import BytesIO
import base64
import traceback

from google import genai
from google.genai import types

from streamlit_image_coordinates import streamlit_image_coordinates

# ==================================================
# CONFIG testv3
# ==================================================
GEMINI_API_KEY = st.secrets.get("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    st.error("GOOGLE_API_KEY missing in Streamlit secrets.")
    st.stop()

MODEL_NAME = "gemini-3-pro-image-preview"
RESOLUTION_MAP = {"1K": 1024, "2K": 2048, "4K": 4096}

# ==================================================
# MAIN PROMPT
# ==================================================
VIRTUAL_TRYON_PROMPT = """
Generate a photorealistic image of a professional Indian fashion model wearing this EXACT lehenga outfit.

FORBIDDEN ACTIONS:
❌ Do NOT redesign
❌ Do NOT beautify
❌ Do NOT correct symmetry
❌ Do NOT enhance embroidery
❌ Do NOT hallucinate missing details

LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Baju / Sleeve
- Blouse Border (Choli Border)
- Upper Waist Seam

STRICTLY DO NOT MAKE ANY CHANGE IN DRESS.

LEHENGA & DUPATTA ACCURACY:
• Replicate lehenga silhouette, flare volume, kalis/panels, pleats, hemline width, embroidery layout, and waistband design.
• Match skirt flow, fold depth, and fabric weight exactly.
• Dupatta must retain original drape style, border design, booti work, transparency level, and fall direction.
• Preserve exact border width, embellishment type, and corner tassels/latkans.

ABSOLUTE CONSTRAINTS:
- Do not modify embroidery geometry
- Do not smooth borders
- Do not interpolate missing patterns
- Pixel-adjacent replication only
- BACKGROUND MUST NEVER MODIFY THE GARMENT, ITS COLORS, SHINE, OR SHAPE
"""

# ==================================================
# DRESS TYPE → BACKGROUND (NEW BLOCK)
# ==================================================
DRESS_BACKGROUND_MAP = {
    "Printed Lehenga": """
BACKGROUND:
Plain simple background.
""",

    "Fusion Dress": """
BACKGROUND:
Plain simple background.
""",

    "Heavy Lehenga": """
BACKGROUND:
Outside royal background.
""",

    "Indo-Western": """
BACKGROUND:
Outside royal background.
""",

    "Gown": """
BACKGROUND:
Outside background.
"""
}

# ==================================================
# POSE PROMPTS
# ==================================================
POSE_PROMPTS = {
    "Natural Standing (Recommended)": """
POSE:
Natural upright standing pose.
Relaxed shoulders.
Even weight distribution.
""",

    "Soft Fashion Pose": """
POSE:
Slight hip shift.
Relaxed arms.
""",

    "Editorial Pose": """
POSE:
Subtle editorial fashion pose.
""",

    "Slight Walk Pose": """
POSE:
Very mild walking stance.
""",

    "Random Natural Pose": """
POSE:
Random natural balanced fashion pose.
"""
}

# ==================================================
# PAGE SETUP
# ==================================================
st.set_page_config(page_title="SRS Try-On", page_icon="👗", layout="wide")
st.title("👗 SRS – Strict Replication Try-On")

# ==================================================
# SIDEBAR
# ==================================================
with st.sidebar:
    st.header("⚙️ Settings")

    resolution_choice = st.selectbox("Resolution", ["1K", "2K", "4K"], index=1)

    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "9:16", "16:9"],
        index=3
    )

    color_mode = st.selectbox(
        "Color Mode",
        ["Automatic", "Manual (Dropper)"]
    )

    dress_type = st.selectbox(
        "👗 Dress Type",
        [
            "Printed Lehenga",
            "Heavy Lehenga",
            "Indo-Western",
            "Fusion Dress",
            "Gown"
        ]
    )

    st.subheader("🧍 Model Pose")

pose_style = st.selectbox(
    "Pose Style",
    list(POSE_PROMPTS.keys()),
    index=0
)

# ==================================================
# IMAGE UPLOADS
# ==================================================
col1, col2 = st.columns(2)

with col1:
    main_file = st.file_uploader("Upload Main Image", type=["jpg", "jpeg", "png"])
    main_image = Image.open(main_file).convert("RGB") if main_file else None
    if main_image:
        st.image(main_image, width='stretch')

with col2:
    ref1_file = st.file_uploader("Upload Choli Image", type=["jpg", "jpeg", "png"])
    ref1_image = Image.open(ref1_file).convert("RGB") if ref1_file else None

    ref2_file = st.file_uploader("Upload Lehenga Image", type=["jpg", "jpeg", "png"])
    ref2_image = Image.open(ref2_file).convert("RGB") if ref2_file else None

# ==================================================
# COLOR PICKER
# ==================================================
blouse_color = "#FFFFFF"
lehenga_color = "#FFFFFF"
dupatta_color = "#FFFFFF"

if color_mode == "Manual (Dropper)" and main_image:
    st.subheader("🎯 Mini Color Picker")

    pick_view = main_image.resize((300, 300))
    coords = streamlit_image_coordinates(pick_view, key="picker")

    if coords:
        px, py = coords["x"], coords["y"]
        ow, oh = main_image.size
        rx = int(px * ow / 300)
        ry = int(py * oh / 300)

        r, g, b = main_image.getpixel((rx, ry))
        picked_hex = f"#{r:02x}{g:02x}{b:02x}"

        st.success(f"Picked Color → {picked_hex}")
        st.markdown(
    f"""
    <div style="
        width:90px;
        height:90px;
        background:{picked_hex};
        border-radius:10px;
        border:2px solid black;
        margin-bottom:10px;
    "></div>
    """,
    unsafe_allow_html=True
)


        target = st.selectbox(
            "Apply picked color to",
            ["Blouse", "Lehenga", "Dupatta"]
        )

        if target == "Blouse":
            blouse_color = picked_hex
        elif target == "Lehenga":
            lehenga_color = picked_hex
        else:
            dupatta_color = picked_hex

# ==================================================
# HELPERS
# ==================================================
def image_to_part(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")

def extract_image(resp):
    for cand in resp.candidates:
        for part in cand.content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.mime_type.startswith("image"):
                data = inline.data
                return base64.b64decode(data) if isinstance(data, str) else data
    return None

# ==================================================
# GENERATE
# ==================================================
pose_prompt = POSE_PROMPTS.get(pose_style, "")
background_prompt = DRESS_BACKGROUND_MAP.get(dress_type, "")

if st.button("🎨 Generate Image"):
    if not main_image:
        st.error("Please upload the main image.")
        st.stop()

    with st.spinner("Generating image…"):
        try:
            color_prompt = f"""
MANUAL COLORS:
Blouse  : {blouse_color}
Lehenga : {lehenga_color}
Dupatta : {dupatta_color}
"""

            final_prompt = (
                VIRTUAL_TRYON_PROMPT
                + color_prompt
                + background_prompt
                + pose_prompt
            )

            parts = [
                types.Part.from_text(text=final_prompt),
                image_to_part(main_image)
            ]

            if ref1_image:
                parts.append(image_to_part(ref1_image))
            if ref2_image:
                parts.append(image_to_part(ref2_image))

            client = genai.Client(api_key=GEMINI_API_KEY)

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=resolution_choice
                    )
                )
            )

            img_bytes = extract_image(response)

            if img_bytes:
                out_img = Image.open(BytesIO(img_bytes)).convert("RGB")
                st.image(out_img, width='stretch')

                buf = BytesIO()
                out_img.save(buf, format="JPEG", quality=95)
                st.download_button(
                    "📥 Download Image",
                    buf.getvalue(),
                    "output.jpg",
                    "image/jpeg"
                )
            else:
                st.error("No image returned by Gemini.")

        except Exception:
            st.error("Generation failed.")
            st.text(traceback.format_exc())
