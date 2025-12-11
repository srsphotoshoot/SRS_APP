import streamlit as st
from PIL import Image
from io import BytesIO

from google import genai
from google.genai import types

# Get API key
GEMINI_API_KEY = st.secrets.get("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    st.error("⚠️ Google API key not found!")
    st.stop()

MODEL_NAME = "gemini-3-pro-image-preview"

# Optimized prompt (shorter but strict)
VIRTUAL_TRYON_PROMPT = """
REFERENCE IMAGE = ABSOLUTE GROUND TRUTH.
Reproduce the outfit exactly. NO color/pattern/silhouette deviation.
FOCUS: SHOULDER + SLEEVE + BOOTA + BLOUSE BORDER
Replicate embroidery, fabric, borders, motifs, and garment structure 1:1.
MODEL: photorealistic Indian model, neutral pose, studio lighting.
STRICT DO NOTS: No alterations, no improvements, exact replication only.
"""

st.set_page_config(page_title="Virtual Lehenga Try-On", page_icon="👗", layout="wide")
st.title("👗 Virtual Lehenga Try-On")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    resolution_option = st.selectbox("Initial Generation Resolution", options=["1K", "2K"], index=1)
    upscale_to_4k = st.checkbox("Upscale to 4K", value=True)
    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        options=["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"],
        index=3
    )

# Upload images
col1, col2 = st.columns([1, 1])
with col1:
    main_file = st.file_uploader("Upload Main Lehenga Image", type=["jpg","jpeg","png"])
    if main_file:
        main_image = Image.open(main_file).convert("RGB")
        st.image(main_image, caption="Main Image", use_container_width=True)

    ref1_file = st.file_uploader("Reference Image 1", type=["jpg","jpeg","png"])
    ref1_image = Image.open(ref1_file).convert("RGB") if ref1_file else None

    ref2_file = st.file_uploader("Reference Image 2", type=["jpg","jpeg","png"])
    ref2_image = Image.open(ref2_file).convert("RGB") if ref2_file else None

generate_btn = st.button("🎨 Generate Model Image")

# Convert PIL to Part
def image_to_part(pil_image: Image.Image) -> types.Part:
    buf = BytesIO()
    pil_image.save(buf, format="PNG")
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")

# AI Upscaler using Gemini itself
def upscale_image(img: Image.Image) -> Image.Image:
    client = genai.Client(api_key=GEMINI_API_KEY)
    parts = [image_to_part(img)]
    content = types.Content(role="user", parts=parts)
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="1:1", image_size="4K")
    )
    response = client.models.generate_content(model=MODEL_NAME, contents=[content], config=config)
    # Extract image bytes
    if response.candidates and response.candidates[0].content.parts:
        data = response.candidates[0].content.parts[0].inline_data.data
        return Image.open(BytesIO(data))
    return img

# Generate
if generate_btn:
    if not main_file:
        st.error("Please upload the main lehenga image!")
    else:
        with st.spinner("🎨 Generating image..."):
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
                # Prepare parts
                parts = [types.Part.from_text(text=VIRTUAL_TRYON_PROMPT), image_to_part(main_image)]
                if ref1_image: parts.append(image_to_part(ref1_image))
                if ref2_image: parts.append(image_to_part(ref2_image))

                content = types.Content(role="user", parts=parts)
                config = types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size=resolution_option)
                )

                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[content],
                    config=config
                )

                # Extract image
                output_image_data = None
                if response.candidates and response.candidates[0].content.parts:
                    part = response.candidates[0].content.parts[0]
                    output_image_data = part.inline_data.data if part.inline_data else None

                if output_image_data:
                    gen_image = Image.open(BytesIO(output_image_data))

                    # Optional upscale
                    if upscale_to_4k:
                        with st.spinner("⬆️ Upscaling to 4K..."):
                            gen_image = upscale_image(gen_image)

                    st.image(gen_image, caption="Generated Image", use_container_width=True)
                    st.download_button("📥 Download", data=BytesIO(output_image_data).getvalue(),
                                       file_name="lehenga_generated.jpg", mime="image/jpg")
                else:
                    st.error("❌ No image generated!")

            except Exception as e:
                st.error(f"❌ Error: {e}")
