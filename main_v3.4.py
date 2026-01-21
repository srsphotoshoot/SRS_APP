import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError
from io import BytesIO
import base64
import traceback

from google import genai
from google.genai import types
from streamlit_image_coordinates import streamlit_image_coordinates

# ==================================================
# PAGE CONFIG deployment ready app
# ==================================================
st.set_page_config(
    page_title="SRS – Strict Replication Try-On",
    page_icon="logo/2.png",
    layout="wide"
)
# ==================================================
# LOGO
# ==================================================
try:
    logo = Image.open("logo/2.png")
    st.sidebar.image(logo, width=200)
    st.sidebar.divider()
except Exception as e:
    st.sidebar.warning(f"⚠️ Could not load logo: {str(e)}")
# ==================================================
# GEMINI CONFIG
# ==================================================
GEMINI_API_KEY = st.secrets.get("SRS_KEY")
if not GEMINI_API_KEY:
    st.error("❌ SRS_KEY missing in Streamlit secrets.")
    st.stop()
MODEL_NAME = "gemini-2.5-flash-image"
# ==================================================
# SESSION STATE
# ==================================================
st.session_state.setdefault("last_generated_image", None)
st.session_state.setdefault("retry_mode", False)
st.session_state.setdefault("final_prompt", "")
st.session_state.setdefault("confirm_redirect", False)
st.session_state.setdefault("main_image", None)
st.session_state.setdefault("main_file_sig", None)
st.session_state.setdefault("ref1_image", None)
st.session_state.setdefault("ref1_file_sig", None)
st.session_state.setdefault("ref2_image", None)
st.session_state.setdefault("ref2_file_sig", None)
# ==================================================
# IMAGE UTILS
# ==================================================

def compress_upload_image(img, upload_quality):
    img= ImageOps.exif_transpose(img)   
    img = img.convert("RGB")

    MAX_DIM = 2048
    w, h = img.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    quality = upload_quality
    best_buf = None
    best_quality = quality
    best_size = 0
    target_min = 1 * 1024 * 1024
    target_max = 2 * 1024 * 1024

    while quality >= 55:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        buf.seek(0, 2)  # Seek to end
        size = buf.tell()  # Get actual size
        
        # If size is in target range, use it
        if target_min <= size <= target_max:
            buf.seek(0)
            compressed_img = Image.open(buf)
            size_mb = round(size / (1024 * 1024), 2)
            st.success(f"✅ Image compressed successfully | Size: {size_mb} MB | Quality: {quality}%")
            return compressed_img
        
        # Keep track of the best match that's >= 1 MB
        if target_min <= size and size > best_size:
            best_buf = buf
            best_quality = quality
            best_size = size
        
        quality -= 2

    # If we couldn't hit target range exactly, use the best match that's >= 1 MB
    if best_buf and best_size >= target_min:
        best_buf.seek(0)
        size_mb = round(best_size / (1024 * 1024), 2)
        st.warning(f"⚠️ Image size: {size_mb} MB | Quality: {best_quality}% (close to target range)")
        return Image.open(best_buf)
    
    # Fallback: increase quality to get closer to 1 MB
    quality = 95
    while quality >= 55:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        buf.seek(0, 2)
        size = buf.tell()
        
        if size >= target_min:
            buf.seek(0)
            size_mb = round(size / (1024 * 1024), 2)
            st.warning(f"⚠️ Image size: {size_mb} MB | Quality: {quality}% (high quality preserved)")
            return Image.open(buf)
        
        quality += 3

    # Last resort: return at quality 95
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95, optimize=True)
    buf.seek(0, 2)
    size = buf.tell()
    size_mb = round(size / (1024 * 1024), 2)
    st.warning(f"⚠️ Image size: {size_mb} MB | Quality: 95%")
    buf.seek(0)
    return Image.open(buf)
#------------------------------------------------------------------
#auto compresor based on size and resolution added 11th june
#------------------------------------------------------------------
def auto_process_image(img, uploaded_file, upload_quality, label="Image"):
    img = ImageOps.exif_transpose(img).convert("RGB")

    size_mb = uploaded_file.size / (1024 * 1024)
    w, h = img.size
    dpi = img.info.get("dpi", (72,))[0]

    needs_compression = False
    reasons = []

    if size_mb > 1.5:
        needs_compression = True
        reasons.append("file size")

    if max(w, h) > 2048:
        needs_compression = True
        reasons.append("high resolution")

    if dpi >= 300 and size_mb < 3:
        needs_compression = False
        reasons = ["professional image"]

    if needs_compression:
        st.info(f"🔧 Auto-compressing {label} ({', '.join(reasons)})")
        img = compress_upload_image(img, upload_quality)
    else:
        st.success(f"✅ {label} kept original quality ({', '.join(reasons)})")

    return img
# ==================================================
# PART CONVERSION
# ==================================================
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
        if not img_bytes:
            st.error("❌ No image data received from API.")
            return None
        img = Image.open(BytesIO(img_bytes))
        img.verify()
        return Image.open(BytesIO(img_bytes))
    except (UnidentifiedImageError, Exception) as e:
        st.error(f"❌ Failed to process image: {str(e)}")
        return None

# ==================================================
# GARMENT-AWARE PROMPTS
# ==================================================
BASE_PROMPT_MAP = {
    "Normal Mode": "Generate a photorealistic image of a professional Indian fashion model wearing this exact dress outfit. Simply add a human model body to the dress - do NOT modify any aspect of the garment.",
    "Printed Lehenga": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT PRINTED LEHENGA outfit.",
    "Heavy Lehenga": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT HEAVY LEHENGA outfit.",
    "Western Dress": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT WESTERN DRESS outfit.",
    "Indo-Western": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT INDO-WESTERN outfit.",
    "Gown": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT GOWN.",
    "Saree": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT SAREE outfit.",
    "Plazo-set": "Generate a photorealistic image of a professional Indian fashion model wearing this EXACT PLAZO-SET outfit."
}

LOCKED_REGION_MAP = {
    "Normal Mode": """
LOCKED REGIONS (ABSOLUTE - DO NOT MODIFY):
- Entire Dress Structure
- All Seams and Construction
- Embroidery and Patterns (if any)
- Fabric Texture and Weave
- All Geometric Details
- Border and Hem Details
- Dupatta (if present)
- ANY and ALL dress components
ONLY add human body to the dress without ANY modifications.
""",
    "Printed Lehenga": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Baju / Sleeve
- Blouse Border
- Upper Waist Seam
- Lehenga Skirt
- Embroidery Pattern
""",
    "Heavy Lehenga": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Baju / Sleeve
- Blouse Border
- Upper Waist Seam
- Heavy Embroidery Details
- Skirt Silhouette
""",
    "Western Dress": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Sleeve ends
- Neckline
- Waist definition
- Dress hem
""",
    "Indo-Western": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Sleeve ends
- Top-to-bottom transition seam
- Waist details
- Bottom silhouette
""",
    "Gown": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Bodice seam
- Waist transition (if present)
- Gown length and flow
""",
    "Saree": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Blouse Back
- Saree Pleats
- Saree Pallu
- Waist definition
- Border Details
""",
    "Plazo-set": """
LOCKED REGIONS (HIGHEST PRIORITY):
- Shoulder
- Kurta Front and Back
- Neckline
- Sleeve Details
- Plazo Length and Fit
- Border Pattern
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
    if dress_type in ["Printed Lehenga", "Heavy Lehenga", "Saree", "Plazo-set"]:
        return DUPATTA_LOCK_PROMPT
    return ""

# ==================================================
# COLOR EXTRACTION FROM PROMPTS
# ==================================================
BACKGROUND_COLOR_OPTIONS = {
    "Normal Mode": ["royal outdoor","royal grey","royal brown","royal cream","royal outdoor garden" ,"fort outdoor","Butique","royal indian fort "],
    "Printed Lehenga": ["royal grey", "royal brown", "royal cream"],
    "Heavy Lehenga": ["royal outdoor", "royal indian fort", "royal palace"],
    "Western Dress": ["royal grey", "royal brown", "royal cream","butique"],
    "Indo-Western": ["royal outdoor", "royal indian fort", "royal palace"],
    "Gown": ["royal outdoor", "royal indian fort", "royal palace"],
    "Saree": ["royal grey", "royal brown", "royal cream","butique"],
    "Plazo-set": ["royal grey", "royal brown", "royal cream", "butique"]
}

# Background descriptions mapping
BACKGROUND_DESCRIPTIONS_MAP = {
    "royal outdoor": "BACKGROUND: Royal outdoor background with elegant settings.",
    "royal grey": "BACKGROUND: Plain simple studio background with royal grey.",
    "royal brown": "BACKGROUND: Plain simple studio background with royal brown.",
    "royal cream": "BACKGROUND: Plain simple studio background with royal cream.",
    "inside butique showroom ": "BACKGROUND: Inside boutique showroom with sophisticated ambiance.",
    "royal outdoor garden": "BACKGROUND: Royal outdoor garden background with natural elegance.",
    "fort outdoor": "BACKGROUND: Fort outdoor background with royal heritage settings.",
    "royal indian fort": "BACKGROUND: Royal outdoor background with Indian fort architecture.",
    "royal palace": "BACKGROUND: Royal outdoor background with palace settings.",
    "Butique": "BACKGROUND: High-end fashion boutique interior.\n- Neutral luxury palette (beige / ivory / warm grey)\n- Polished stone or marble flooring\n- Soft warm ambient lighting with diffused ceiling spotlights\n- Minimal gold/brass accents\n- Sparse clothing racks far in background\n- Shallow depth-of-field, background softly blurred\n- No mannequins, mirrors, signage, or logos\n- Background must NOT alter garment colors\n"
}

# Ornate backgrounds for specific dress types (kept for backward compatibility)
ORNATE_BACKGROUND_DESCRIPTIONS = {
    "Heavy Lehenga": "BACKGROUND: Royal outdoor background with ornate settings.",
    "Indo-Western": "BACKGROUND: Royal outdoor background with contemporary elegance.",
    "Gown": "BACKGROUND: Elegant outdoor background with sophisticated ambiance."
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
def build_final_prompt(
    dress_type,
    blouse_color,
    lehenga_color,
    dupatta_color,
    background_color,
    pose_style
):
    # --------------------------------------------------
    # BACKGROUND SELECTION
    # --------------------------------------------------
    # First check if there's a specific description for this background color
    if background_color in BACKGROUND_DESCRIPTIONS_MAP:
        background_prompt = BACKGROUND_DESCRIPTIONS_MAP[background_color]
    # Then check if this dress type has ornate background descriptions
    elif dress_type in ORNATE_BACKGROUND_DESCRIPTIONS:
        background_prompt = ORNATE_BACKGROUND_DESCRIPTIONS[dress_type]
    # Default fallback
    else:
        background_prompt = f"BACKGROUND: {background_color}."

    # --------------------------------------------------
    # NORMAL MODE SPECIAL HANDLING
    # --------------------------------------------------
    if dress_type == "Normal Mode":
        return (
            BASE_PROMPT_MAP[dress_type]
            + """

MODEL SPECIFICATION (MANDATORY):
- Adult Indian female fashion model
- Neutral body proportions
- Standard runway posture
- Studio photoshoot lighting
- No stylization, no glamour exaggeration
"""

            + """
MANNEQUIN-TO-MODEL TRANSFER (ABSOLUTE PRIORITY):
- Source image shows a MANNEQUIN or dress form, not a human
- Garment MUST be transferred onto a REAL HUMAN MODEL
This is a garment-to-body projection task with strict visual preservation
- Preserve EVERY SINGLE detail:
  * All stitches and seams
  * All embroidery and embellishments
  * All geometric curves and drape
  * All patterns and prints
  * All colors and textures
  * All borders and hems
  * The entire silhouette exactly as is
- Minor geometric adjustment is allowed ONLY where physically unavoidable to fit a human body
- Adjustments must NOT be noticeable to a human observer

- Adjust ONLY for natural human anatomy and gravity fitting
- This is a BODY ADDITION task, not a design modification task
""" 
+ """DUPATTA POSITION & LENGTH LOCK (CRITICAL):
- If a dupatta is visible in the reference image, it MUST be preserved exactly
- Preserve the SAME dupatta length relative to the garment
- Preserve the SAME visible coverage (front / side / back)
- If the dupatta is:
  * Half visible → keep it half visible
  * Only at the back → keep it only at the back
  * Folded or draped asymmetrically → preserve the asymmetry
- Do NOT extend, shorten, reposition, or re-drape the dupatta
- Do NOT bring the dupatta to the front if it is not visible in front
- Do NOT “complete” or “beautify” missing sections
- Treat the dupatta as a fixed spatial object, not a styling element
"""

            + """
CRITICAL - ABSOLUTELY FORBIDDEN (VIOLATION = FAIL):
- Do NOT redesign any part of the dress
- Do NOT beautify or enhance anything
- Do NOT correct any asymmetry
- Do NOT modify embroidery or patterns
- Do NOT hallucinate missing details
- Do NOT add or remove any garment component
- Do NOT change any colors
- Do NOT alter fabric texture or weight
- Do NOT change the silhouette or fit
- Do NOT modify seams, hems, or borders
- This is a body-projection task with minimal unavoidable physical fitting only

"""

            + LOCKED_REGION_MAP[dress_type]
            + "\n"
            + background_prompt
            + "\n"
            + POSE_PROMPTS[pose_style]
        )

    # --------------------------------------------------
    # STANDARD MODE (Original logic for other dress types)
    # --------------------------------------------------
    return (
        # ===============================
        # CORE GENERATION INTENT
        # ===============================
        BASE_PROMPT_MAP[dress_type]
        + """

MODEL SPECIFICATION (MANDATORY):
- Adult Indian female fashion model
- Neutral body proportions
- Standard runway posture
- Studio photoshoot lighting
- No stylization, no glamour exaggeration
"""

        # ===============================
        # MANNEQUIN → MODEL TRANSFER
        # ===============================
        + """
MANNEQUIN-TO-MODEL TRANSFER (CRITICAL):
- Source image shows a MANNEQUIN, not a human
- Garment MUST be transferred onto a REAL HUMAN MODEL
- Preserve original garment geometry and proportions
- Adjust ONLY for natural human anatomy and gravity
- Do NOT alter cut, seams, flare, or embroidery layout
- Blouse fit must follow mannequin reference exactly
- Lehenga flare, fall, and volume must remain unchanged
"""

        # ===============================
        # FORBIDDEN ACTIONS
        # ===============================
        + """
FORBIDDEN ACTIONS (ABSOLUTE):
- Do NOT redesign
- Do NOT beautify
- Do NOT correct symmetry
- Do NOT enhance embroidery
- Do NOT hallucinate missing details
- Do NOT add accessories or jewelry
- Do NOT remove any visible garment component
"""

        # ===============================
        # LOCKED REGIONS
        # ===============================
        + LOCKED_REGION_MAP[dress_type]

        # ===============================
        # DUPATTA ENFORCEMENT
        # ===============================
        + get_dupatta_prompt(dress_type)
        + """
DUPATTA PRESENCE RULE:
- IF dupatta is visible in the reference image, it MUST be present in the output
- Dupatta drape must match reference placement and length
"""

        # ===============================
        # GARMENT CLASS SAFETY
        # ===============================
        + """
GARMENT CLASS LOCK (ABSOLUTE):
- DO NOT reinterpret lehengas as gowns or dresses
- DO NOT reinterpret gowns or indo-western outfits as lehengas
- DO NOT add a dupatta if it does NOT exist in reference
"""

        # ===============================
        # COLOR LOCKS
        # ===============================
        + f"""
HIGH-PRIORITY COLOR LOCK (HEX):
- Blouse: {blouse_color}
- Lehenga: {lehenga_color}
- Dupatta: {dupatta_color}
"""

        # ===============================
        # PHYSICAL & PIXEL CONSTRAINTS
        # ===============================
        + """
ABSOLUTE CONSTRAINTS:
- Visual identity replication (viewer must perceive the same product)
- Background must NOT affect garment colors
- Lighting must NOT wash out embroidery
- No motion, no wind, no fabric lift
"""

        # ===============================
        # BACKGROUND & POSE
        # ===============================
        + "\n"
        + background_prompt
        + "\n"
        + POSE_PROMPTS[pose_style]
    )

# ==================================================
# UI
# ==================================================
st.title("SRS – Strict Replication Try-On")

with st.sidebar:
    upload_quality = st.slider("Upload Image Quality", 60, 95, 85)
   # disable_compression = st.toggle("🚫 Disable Image Compression", value=False) 11 january   
    generation_resolution = st.selectbox("Generation Resolution", ["1K", "2K", "4K"], index=1)
    aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "2:3", "3:4", "4:5", "9:16"], index=2)
    dress_type = st.selectbox("Dress Type", [
        "Normal Mode",
        "Printed Lehenga",
        "Heavy Lehenga",
        "Western Dress",
        "Indo-Western",
        "Gown",
        "Saree",
        "Plazo-set"
    ])
    pose_style = st.selectbox("Pose Style", list(POSE_PROMPTS.keys()))
    color_mode = st.selectbox("Color Mode", ["Automatic", "Manual (Dropper)"])

# ==================================================
# IMAGE INPUTS
# ==================================================
st.subheader("📸 Main Image")
main_file = st.file_uploader(
    "Upload Main Image",
    ["jpg", "jpeg", "png"],
    key="main_image_uploader"
)
if main_file:
    sig = (
    main_file.name,
    main_file.size,
    hash(main_file.getbuffer().tobytes())
)


    if st.session_state.main_file_sig != sig:
        img = Image.open(main_file)

        img = auto_process_image(
        img,
        main_file,
        upload_quality,
        label="Main Image"
        )

        st.session_state.main_image = img
        st.session_state.main_file_sig = sig


    main_image = st.session_state.main_image
else:
    main_image = None
    st.session_state.main_file_sig = None
    st.session_state.main_image = None

if main_image:
    st.image(main_image, width="stretch")

st.subheader("📚 Reference Images")
ref1_file = st.file_uploader(
    "Upload Choli Reference",
    ["jpg", "jpeg", "png"],
    key="choli_ref_uploader"
)
if ref1_file:
    sig = (
        ref1_file.name,
        ref1_file.size,
        hash(ref1_file.getbuffer().tobytes())
    )

    if st.session_state.ref1_file_sig != sig:
        img = Image.open(ref1_file)

        img = auto_process_image(
    img,
    ref1_file,
    upload_quality,
    label="Choli Reference"
)


        st.session_state.ref1_image = img
        st.session_state.ref1_file_sig = sig

    ref1_image = st.session_state.ref1_image
else:
    ref1_image = None
    st.session_state.ref1_image = None
    st.session_state.ref1_file_sig = None


ref2_file = st.file_uploader(
    "Upload Lehenga Reference",
    ["jpg", "jpeg", "png"],
    key="lehenga_ref_uploader"
)
if ref2_file:
    sig = (
        ref2_file.name,
        ref2_file.size,
        hash(ref2_file.getbuffer().tobytes())
    )

    if st.session_state.ref2_file_sig != sig:
        img = Image.open(ref2_file)

        img = auto_process_image(
    img,
    ref2_file,
    upload_quality,
    label="Lehenga Reference"
)


        st.session_state.ref2_image = img
        st.session_state.ref2_file_sig = sig

    ref2_image = st.session_state.ref2_image
else:
    ref2_image = None
    st.session_state.ref2_image = None
    st.session_state.ref2_file_sig = None

# ==================================================
# BACKGROUND COLOR SELECTOR (DROPDOWN)
# ==================================================
available_bg_colors = BACKGROUND_COLOR_OPTIONS.get(dress_type, ["royal grey"])
background_color_selected = st.selectbox("Select Background Color", available_bg_colors)
background_color = background_color_selected  # Store for prompt

# ==================================================
# COLOR PICKER (PIXEL-ACCURATE)
# ==================================================
blouse_color = lehenga_color = dupatta_color = "#FFFFFF"
if color_mode == "Manual (Dropper)" and main_image is not None:
    st.subheader("🎯 Manual Color Picker")
    st.info("💡 Enable the picker and click on the image to pick a color")

    # 🔒 Gate picker to prevent rerun/loader issues
    if st.checkbox("🎯 Enable Color Picker"):
        coords = streamlit_image_coordinates(main_image, key="picker")
    else:
        coords = None

    # 🔍 Process only when a valid click exists
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

        # ==================================================
        # 🔍 MAGNIFIER & PIXEL VIEW
        # ==================================================
        st.markdown("**🔍 Magnified View**")

        mag_size = 20
        x_start = max(0, real_x - mag_size)
        x_end = min(orig_w, real_x + mag_size)
        y_start = max(0, real_y - mag_size)
        y_end = min(orig_h, real_y + mag_size)

        mag_region = main_image.crop((x_start, y_start, x_end, y_end))
        mag_region_enlarged = mag_region.resize((300, 300), Image.NEAREST)
        st.image(mag_region_enlarged, width="stretch")

        # ==================================================
        # 📊 PIXEL INFORMATION
        # ==================================================
        st.markdown("**📊 Pixel Information**")

        swatch = Image.new("RGB", (150, 150), (r, g, b))
        st.image(swatch, width=150)

        st.markdown(
            f"""
            **Picked Color:**
            - **HEX:** `{picked_hex}`
            - **RGB:** `({r}, {g}, {b})`
            - **Position:** `({real_x}, {real_y})`
            """
        )

        st.divider()

        # ==================================================
        # 🎯 APPLY COLOR
        # ==================================================
        target = st.selectbox(
            "Apply picked color to",
            ["Blouse", "Lehenga", "Dupatta"],
            key="color_apply_target"
        )

        if target == "Blouse":
            blouse_color = picked_hex
        elif target == "Lehenga":
            lehenga_color = picked_hex
        else:
            dupatta_color = picked_hex

# 🔗 External Redirect Button
if st.sidebar.button("🔗 FEEDBACK HERE"):
    st.session_state.confirm_redirect = True

# ⚠️ Confirmation Popup (Streamlit-style)
if st.session_state.confirm_redirect:
    st.sidebar.warning("⚠️ Are you sure you want to leave this app?")

    if st.sidebar.button("✅ Yes"):
        st.markdown(
    """
    <a href="https://forms.gle/uJ3NwZKthifgF5Q88"
       target="_blank"
       rel="noopener noreferrer">
       👉 Click here to open the form
    </a>
    """,
    unsafe_allow_html=True
)

        st.session_state.confirm_redirect = False

    if st.sidebar.button("❌ No"):
        st.session_state.confirm_redirect = False

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
                dress_type, blouse_color, lehenga_color, dupatta_color, background_color, pose_style
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

            if not response:
                st.error("❌ API did not return a valid response. Try adjusting resolution or trying again.")
                st.stop()

            img_bytes = extract_image_safe(response)
            if not img_bytes:
                st.error("❌ No image data in API response. The model may have failed to generate the image.")
                st.stop()

            out_img = safe_open_image(img_bytes)
            if not out_img:
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

                if not response:
                    st.error("❌ API did not return a valid response. Try again.")
                    st.stop()

                img_bytes = extract_image_safe(response)
                if not img_bytes:
                    st.error("❌ No image data in API response.")
                    st.stop()

                out_img = safe_open_image(img_bytes)
                if not out_img:
                    st.stop()
                
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
