import streamlit as st
from PIL import Image
from io import BytesIO
import base64

from google import genai
from google.genai import types

# Get API key from Streamlit secrets
GEMINI_API_KEY = st.secrets.get("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    st.error("⚠️ Google API key not found in Streamlit secrets!")
    st.stop()

MODEL_NAME = "gemini-3-pro-image-preview"

# Prompt
VIRTUAL_TRYON_PROMPT = """Generate a photorealistic image of a professional Indian fashion model wearing this EXACT dress outfit.  
The uploaded outfit is the ABSOLUTE GROUND TRUTH. Reproduce it with ZERO deviation.  
No reinterpretation. No redesign. No missing details. 1:1 replication required.

=====================
PRIMARY FOCUS AREAS
=====================
SHOULDER • SLEEVE (BAJU) • BOOTA • BLOUSE/CHOLI BORDER  
These areas must be replicated with the highest accuracy.

---------------------
1. SHOULDER ACCURACY
---------------------
• Match the exact shoulder shape, slope, width, curvature, orientation, seam placement, fabric tension, and drape.  
• Preserve shoulder-to-neckline continuity exactly.  
• No stretching, shifting, lifting, distortion, or fabricated geometry.

-------------------
2. SLEEVE PRECISION
-------------------
• Exact sleeve type, length, cut, fit, tightness/looseness, seam structure, and hem finish.  
• Sleeve geometry must match 1:1 with reference.  
• No simplification of embroidery or pattern on sleeves.

------------------------
3. BOOTA/EMBROIDERY WORK
------------------------
• Perfectly copy motifs on shoulder and sleeves: size, density, spacing, alignment, stitching direction, and position.  
• Preserve all embroidery types EXACTLY: zari, resham, dabka, sequins, stones, pearls, mirror work, beads, applique, patchwork, lace, aari work.  
• Metallic shine, reflectivity, thread thickness, stitch texture, and micro-details must match the original precisely.

-------------------------
4. BLOUSE/CHOLI BORDERS
-------------------------
• Replicate neckline border, shoulder-edge borders, sleeve-hem borders, and bottom blouse border EXACTLY.  
• Maintain width, pattern, spacing, metallic tone (gold/silver/copper), and embroidery details with perfect fidelity.  
• No resizing, redesigning, or altering border embellishments.

=========================
COLOR PRESERVATION (KEY)
=========================
• Match the EXACT base color and every secondary color, including embroidery, borders, motifs, and threads.  
• ZERO tolerance for color shift: no hue change, no saturation change, no brightness change.  
• Preserve exact color contrast, gradients, ombre effects, multispectral color behavior, and reflective properties.  
• Metallic colors must retain identical sheen, shine, glow, and reflectivity.  
• Do not brighten, recolor, oversaturate, dull, or tone-correct beyond minor clarity enhancement.

===================
FABRIC REPLICATION
===================
• Match EXACT fabric type: silk, velvet, georgette, net, tulle, brocade, satin, organza, raw silk, Banarasi, etc.  
• Preserve weave pattern, grain direction, surface texture, micro-imperfections, shine/matte ratio.  
• Maintain identical drape, folds, weight distribution, transparency/opacity level, and how fabric interacts with light.  
• NO smoothing, altering, stylizing, polishing, or AI reinterpretation.

=========================================
UPPER BODY STRUCTURE & FIT (CRITICAL ZONE)
=========================================
• Maintain realistic and natural garment-body interaction.  
• Exact chest/cleavage coverage as shown in reference.  
• Blouse must adhere naturally to the torso with correct tension.  
• Waist region must stay fully connected — no detachment, warping, or cloth misalignment.  
• Shoulder → neckline → chest → upper waist must have continuous anatomical logic.

===========================
dress & DUPATTA ACCURACY
===========================
• Replicate dress silhouette, flare volume, kalis/panels, pleats, hemline width, embroidery layout, and waistband design.  
• Match skirt flow, fold depth, and fabric weight exactly.  
• Dupatta must retain original drape style, border design, booti work, transparency level, and fall direction.  
• Preserve exact border width, embellishment type, and corner tassels/latkans.

==============================
PATTERN & MOTIF CONSISTENCY
==============================
• Match all geometric, floral, paisley, vine, traditional motifs EXACTLY—shape, size, alignment, spacing, rotation.  
• Keep pattern repeat cycles identical.  
• No missing motifs, no extra motifs, no alternate variations, no resizing.

=========================
SHINE, SPARKLE & DETAILS
=========================
• Preserve shimmer/sparkle effects, metallic highlights, crystal reflections, and stone glints exactly as captured in the reference.  
• Maintain natural shadowing from folds and borders; do not alter shadow placement.

==========================================
MODEL & PRESENTATION (NEUTRAL + NATURAL)
==========================================
• Photorealistic Indian fashion model.  
• Natural posture; clean studio background (white/soft grey).  
• Soft, even lighting to preserve true outfit color.  
• Full-body or mid-length framing acceptable.  
• Focus remains entirely on the outfit, not on beautification.

=================
DO NOT CHANGE ANYTHING
=================
✗ No color changes  
✗ No design modifications  
✗ No pattern/alignment shifts  
✗ No border width or layout changes  
✗ No sleeve or neckline alteration  
✗ No fabric reinterpretation  
✗ No missing or added embroidery  
✗ No stylization or smoothing  
✗ No unrealistic lighting  
✗ No invented textures or draping  
✗ No accessories unless present in reference  

================
FINAL OBJECTIVE
================
Produce a **2K, ultra-sharp, fashion catalog quality** try-on image where the SHOULDER, SLEEVE, BOOTA, and BORDER regions match the reference with **pixel-level accuracy**, and all colors, textures, patterns, and fabric behaviors are **identical to the input outfit** with ZERO deviation.
"""


st.set_page_config(page_title="SRS-TRY-ON", page_icon="👗", layout="wide")
st.title("👗 SHREE RADHA STUDIO TRY-ON")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings")
    resolution = st.selectbox("Resolution", options=["1K", "2K", "4K"], index=0)
    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        options=["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"],
        index=3
    )
    NOTEBOX = st.markdown("""
**NOTEBOX**

keep upload file size between  
**1–2 MB** for better results  
2K generation suggested.  
**SOURYA**
""")
# Image upload columns
col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("📤 Upload Main dress Image")
    main_image_file = st.file_uploader("Main Image", type=["jpg", "jpeg", "png"])
    if main_image_file:
        main_image = Image.open(main_image_file).convert("RGB")
        st.image(main_image, caption="Main Image", use_container_width=True)

    st.subheader("📤 **CHOLI IMAGE**")
    ref1_file = st.file_uploader("Reference Image 1", type=["jpg", "jpeg", "png"])
    ref1_image = Image.open(ref1_file).convert("RGB") if ref1_file else None

    st.subheader("📤 dress or LOWER PORTION")
    ref2_file = st.file_uploader("Reference Image 2", type=["jpg", "jpeg", "png"])
    ref2_image = Image.open(ref2_file).convert("RGB") if ref2_file else None

generate_btn = st.button("🎨 Generate Model Image")

# Helper function to convert PIL image to Part
def image_to_part(pil_image: Image.Image) -> types.Part:
    img_bytes = BytesIO()
    pil_image.save(img_bytes, format="PNG")
    return types.Part.from_bytes(data=img_bytes.getvalue(), mime_type="image/png")

# Generate image
if generate_btn:
    if not main_image_file:
        st.error("Please upload the main dress image!")
    else:
        st.snow()
        with st.spinner("🎨 Generating image..."):
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)

                # Prepare parts list
                parts = [types.Part.from_text(text=VIRTUAL_TRYON_PROMPT), image_to_part(main_image)]
                if ref1_image:
                    parts.append(image_to_part(ref1_image))
                if ref2_image:
                    parts.append(image_to_part(ref2_image))

          
                content = types.Content(role="user", parts=parts)

           
                config = types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size=resolution)
                )

                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[content],
                    config=config
                )

                output_image_data = None
                description_text = ""

                if hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate.content, "parts"):
                        for part in candidate.content.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                output_image_data = part.inline_data.data
                            if hasattr(part, "text") and part.text:
                                description_text += part.text

                if output_image_data:
                    generated_image = Image.open(BytesIO(output_image_data))
                    st.image(generated_image, caption=f"Generated Image ({resolution} - {aspect_ratio})", use_container_width=True)
                    st.download_button(
                        label="📥 Download Generated Image",
                        data=output_image_data,
                        file_name=f"dress_tryon_{resolution}_{aspect_ratio.replace(':','x')}.jpg",
                        mime="image/jpg"
                    )
                    if description_text:
                        with st.expander("📄 Generation Details"):
                            st.write(description_text)
                else:
                    st.error("❌ No image was generated. Check model access, API key, and SDK version.")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.exception(e)
