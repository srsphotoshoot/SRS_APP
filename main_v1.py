import streamlit as st
from PIL import Image
from io import BytesIO
import base64

from google import genai
from google.genai import types

# Get API Key
GEMINI_API_KEY = st.secrets.get("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    st.error("⚠️ Google API key not found in Streamlit secrets!")
    st.stop()

MODEL_NAME = "gemini-3-pro-image-preview"

# Your prompt
VIRTUAL_TRYON_PROMPT ="""Generate a photorealistic image of a professional fashion model wearing this EXACT lehenga outfit.
Preserve every detail of the original lehenga design exactly as it appears pattern, color, embroidery, waist shape, style, and skirt flow.
Maintain proper body alignment, realistic fitting, and correct cloth tension around the waist, chest, cleavage area, and lower abdominal region.
Make sure the blouse and lehenga sit naturally and continuously without gaps or separation at the belly area.
Ensure the chest and cleavage area appear natural and match the reference garment’s coverage level.
The waist region must stay fully connected and not look detached.
Preserve the original fabric texture, shine, and drape exactly as shown.
Do not redesign or modify any part of the dress.
Only adjust lighting slightly to improve clarity while keeping the original style.
The output must look like a natural photograph, not a generated illustration
Analyze the original outfit extremely carefully and recreate the design with maximum anatomical accuracy. 
Focus especially on:
FOCUS AREA: SHOULDER + BAJU + BOOTA + BLOUSE BORDER

Recreate the outfit with ultra-high accuracy, giving the highest priority to the SHOULDER REGION and everything connected to it. The generated image must preserve:

1. SHOULDER ACCURACY (TOP PRIORITY)
   • Replicate the exact shoulder structure, slope, width, and angle from the reference.
   • Maintain perfect continuity between shoulder, neckline, and upper torso.
   • Preserve the exact way the blouse/choli sits on the shoulder without any redesign.
   • No distortion, stretching, lifting, or shifting of shoulder fabric.

2. BAJU (SLEEVE) PRECISION
   • Match the exact sleeve length: cap, short, 3/4, full, etc. as in the original.
   • Reproduce the exact sleeve cut, fit, and drape.
   • Maintain the correct sleeve tightness/looseness exactly.
   • Keep the sleeve geometry identical—no stylization, no alteration.

3. BOOTA / EMBROIDERY ON SHOULDER & SLEEVES
   • PERFECT replication of all motifs, booti work, floral work, and patterns on:
       - the shoulder
       - sleeve top
       - entire baju surface
   • Exact size, density, spacing, alignment, and thread direction.
   • Match zari, resham, mirror work, sequins, stonework or any embellishment with microscopic precision.
   • DO NOT change any motif shape or placement.

4. BLOUSE / CHOLI BORDER ACCURACY
   • Replicate the exact border design on:
       - neckline border
       - shoulder border (if present)
       - sleeve hem border
       - blouse/choli lower border
   • Match border width, colors, metallic tones, and embroidery EXACTLY.
   • Preserve border spacing and alignment around the shoulder and sleeves.

5. FABRIC & COLOR CONSISTENCY
   • Match the exact fabric type and texture on shoulder + sleeves.
   • Maintain original color shade, saturation, and brightness perfectly.
   • No color shift, no tone mismatch, no incorrect gradients.
   • Keep fabric drape and fall naturally continuous.

6. UPPER BODY STRUCTURAL INTEGRITY
   • Maintain correct connection between shoulder → neckline → chest → upper waist.
   • Avoid belly/chest separation or unrealistic joints.
   • Keep blouse/choli shape identical to the reference.

GOAL:
Produce a photorealistic try-on image where the SHOULDER AREA, BAJU, BOOTA, and BLOUSE/CHOLI BORDER are reproduced with PERFECT fidelity. No redesign, no simplification, no missing details. The output must match the original outfit’s upper structure with 100% accuracy.


COLOR PRESERVATION (CRITICAL):
✓ Match the EXACT base color and all secondary colors with perfect accuracy
✓ Preserve the exact shade, tone, saturation, and brightness of every color
✓ Maintain the exact color gradients, ombre effects, or color transitions
✓ Keep metallic colors (gold, silver, copper) with the same metallic finish and sheen
✓ Replicate the exact color of threads, sequins, stones, and embellishments
✓ Match border colors precisely
✓ Preserve the exact color contrast between different elements

🧵 EMBROIDERY & EMBELLISHMENTS (MICROSCOPIC DETAIL):
✓ Replicate EVERY embroidery pattern with exact placement and density
✓ Copy the exact type of embroidery work: zari, zardozi, gota patti, resham, dabka, kundan, etc.
✓ Maintain the exact size, shape, and arrangement of sequins, beads, and stones
✓ Preserve mirror work (aari work) placement and patterns exactly
✓ Keep the exact thread work direction and stitching style
✓ Replicate pearl, crystal, or stone embellishments with same size and placement
✓ Match the density and coverage of embellishment work precisely
✓ Preserve cutwork, applique, or patchwork exactly as shown
✓ Maintain lace work, tassel work, or fringe details identically

📐 PATTERN & MOTIF ACCURACY:
✓ Replicate geometric patterns (diamonds, squares, chevrons) with exact proportions
✓ Copy floral motifs with the same flower types, sizes, and arrangements
✓ Maintain paisley designs with identical shapes and orientations
✓ Preserve traditional motifs (peacock, lotus, mango, vine) exactly
✓ Keep the exact spacing between pattern repeats
✓ Replicate border patterns with precise width and design
✓ Match the symmetry or asymmetry of patterns exactly
✓ Preserve print patterns if any, with exact colors and clarity

🎀 LEHENGA SKIRT DETAILS:
✓ Match the exact silhouette: A-line, flared, mermaid, circular, or umbrella cut
✓ Replicate the exact flare volume and how it falls
✓ Preserve the exact number and placement of kalis (panels)
✓ Match the exact length and hemline style
✓ Keep the exact waistband design and width
✓ Replicate can-can or lining visibility if any
✓ Preserve pleating, gathering, or draping style exactly
✓ Match the exact flow and movement of the fabric

👚 BLOUSE/CHOLI PRECISION:
✓ Replicate the EXACT neckline: round, V-neck, sweetheart, boat, square, halter, etc.
✓ Match the exact sleeve style: sleeveless, cap, short, 3/4, full, bell, puff, etc.
✓ Preserve the exact sleeve length and fit
✓ Copy the exact back design: open back, keyhole, zip, button, tie-up, hook
✓ Maintain the exact blouse length and fit (crop, fitted, loose)
✓ Replicate collar details if any
✓ Match the exact embroidery and embellishment on the blouse
✓ Preserve blouse fabric texture and color exactly

🧣 DUPATTA ACCURACY:
✓ Match the exact dupatta draping style: one-shoulder, both-shoulder, lehenga style, cape style
✓ Replicate the exact fabric transparency/opacity level
✓ Preserve border width, design, and embellishment exactly
✓ Match the exact length and how it falls
✓ Keep corner tassels, latkan, or gota patti work identical
✓ Replicate body embellishments or booti work exactly
✓ Maintain the exact placement and pinning style

🧶 FABRIC & TEXTURE REPLICATION:
✓ Match the exact fabric type: silk, velvet, georgette, net, tulle, organza, brocade, satin, raw silk, chanderi, banarasi, etc.
✓ Replicate the exact fabric texture: smooth, matte, glossy, embossed, crushed, etc.
✓ Preserve the exact fabric sheen and light reflection
✓ Match the fabric weight appearance (heavy vs light)
✓ Replicate any visible weave patterns in the fabric
✓ Maintain the exact fabric drape and fall
✓ Preserve layering effects if multiple fabric layers are visible

💎 BORDER & FINISHING DETAILS:
✓ Replicate ALL border designs with exact width and pattern
✓ Match the exact border embellishment type and density
✓ Preserve corner designs and how borders meet
✓ Keep piping, lace, or trim details identical
✓ Replicate gota patti border work exactly
✓ Match the border color contrast precisely

📏 STRUCTURAL ACCURACY:
✓ Maintain the exact garment proportions and fit
✓ Replicate how the outfit sits on the body
✓ Preserve the exact length ratios between blouse, skirt, and dupatta
✓ Match the exact volume and fullness of the lehenga
✓ Keep the waistline position exact
✓ Replicate any visible stitching lines or seams

🌟 SPECIAL EFFECTS & DETAILS:
✓ Preserve any shimmer, shine, or sparkle effects
✓ Replicate metallic accents with same metallic tone
✓ Match any gradient or ombre effects precisely
✓ Keep shadow effects from layering identical
✓ Preserve any 3D embellishments (flowers, appliques)
✓ Replicate any contrast panels or color blocking exactly

👤 MODEL & PRESENTATION:
• Professional Indian fashion model with elegant features
• Graceful standing pose in traditional lehenga style
• Hands positioned naturally: one hand holding dupatta or resting gracefully
• Neutral, clean studio background (soft grey or white backdrop)
• Professional studio lighting: soft, even lighting showing all details clearly
• Model facing forward or at a slight 20-30 degree angle
• Full-length shot showing the entire outfit from head to toe
• Focus on the outfit, not the model's face
• Natural, elegant posture with good body language
• Clear visibility of all three components: lehenga, blouse, and dupatta

📸 IMAGE QUALITY REQUIREMENTS:
• High-resolution, crystal-clear, professional fashion photography quality
• Perfect lighting to showcase all embroidery and embellishment details
• Sharp focus on fabric texture and design elements
• Professional color grading and white balance
• No blur, no distortion, no artifacts
• Magazine-quality fashion catalog photograph

🚫 STRICT PROHIBITIONS - DO NOT:
✗ Change ANY color or shade whatsoever
✗ Modify, simplify, or omit ANY pattern or design element
✗ Alter embroidery placement, type, or density
✗ Change fabric type, texture, or sheen
✗ Modify the silhouette or cut of any garment piece
✗ Add new design elements not present in the original
✗ Change border designs or widths
✗ Alter the draping style of the dupatta
✗ Simplify complex embellishment work
✗ Change the neckline, sleeve style, or blouse design
✗ Modify the length or proportions of any component
✗ Use different metallic tones (gold vs silver)
✗ Change the background to anything distracting
✗ Add accessories not present in original (jewelry, props)


The output must look like a professional fashion catalog photo with the model wearing THIS EXACT lehenga design and the image should be in 2k quality."""



# Page config
st.set_page_config(page_title="Virtual Lehenga Try-On (4K)", page_icon="👗", layout="wide")
st.title("👗 Virtual Lehenga Try-On - High Resolution")
st.markdown("Upload your lehenga image and generate a professional **high-resolution** model try-on image")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Image Generation Settings")
    resolution = st.selectbox("Output Resolution", ["1K", "2K", "4K"], index=2)
    aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"], index=3)
    st.divider()
    st.info("📦 Make sure you've installed the NEW SDK:\n```\npip uninstall google-generativeai\npip install google-genai\n```")
    st.caption(f"📐 Selected: {aspect_ratio} at {resolution} resolution")
    st.caption(f"🔧 Model: {MODEL_NAME}")

# Layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Lehenga Image")
    uploaded_file = st.file_uploader("Choose a lehenga image", type=["jpg","jpeg","png"])
    if uploaded_file:
        input_image = Image.open(uploaded_file).convert("RGB")
        st.caption(f"Input: {input_image.width}x{input_image.height}px")
        st.image(input_image, caption="Input Lehenga", use_container_width=True)
        with st.expander("📝 View Generation Prompt"):
            st.text_area("Prompt", VIRTUAL_TRYON_PROMPT, height=300, disabled=True)
    generate_btn = st.button("🎨 Generate Model Image", type="primary", use_container_width=True)

with col2:
    st.subheader("✨ Generated Result")
    output_placeholder = st.empty()
    if not uploaded_file:
        output_placeholder.info("👈 Upload a lehenga image to get started")

# Generation Logic
if generate_btn:
    if not uploaded_file:
        st.error("Please upload a lehenga image first!")
    else:
        with st.spinner(f"🎨 Generating {resolution} resolution model image..."):
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)

                # Convert input image to bytes
                img_bytes_io = BytesIO()
                input_image.save(img_bytes_io, format="PNG")
                img_bytes = img_bytes_io.getvalue()

                # Create image part
                image_part = types.Part.from_bytes(data=img_bytes, mime_type='image/png')

                # Generate config
                config = types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE'],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size=resolution)
                )

                # Generate
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[VIRTUAL_TRYON_PROMPT, image_part],
                    config=config
                )

                # Extract result
                description_text = ""
                output_image_data = None

                if hasattr(response, "parts"):
                    for part in response.parts:
                        # Text
                        if hasattr(part, "text") and part.text:
                            description_text += part.text

                        # Image via as_image()
                        if hasattr(part, "as_image"):
                            try:
                                img = part.as_image()
                                if img:
                                    buf = BytesIO()
                                    img.save(buf, format="PNG")
                                    output_image_data = buf.getvalue()
                            except:
                                pass

                        # Fallback: inline_data
                        if hasattr(part, "inline_data"):
                            try:
                                inline = part.inline_data
                                if hasattr(inline, "data"):
                                    img_data = inline.data
                                    if isinstance(img_data, (bytes, bytearray)):
                                        output_image_data = img_data
                                    elif isinstance(img_data, str):
                                        output_image_data = base64.b64decode(img_data)
                            except Exception as e:
                                st.write(f"⚠️ inline_data extraction failed: {e}")

                # Display image
                with col2:
                    if output_image_data:
                        generated_image = Image.open(BytesIO(output_image_data))
                        st.caption(f"✅ Generated: {generated_image.width}x{generated_image.height}px at {resolution}")
                        output_placeholder.image(generated_image, caption=f"Generated Model Image ({resolution} - {aspect_ratio})", use_container_width=True)
                        st.download_button(
                            label=f"📥 Download {resolution} Image",
                            data=output_image_data,
                            file_name=f"lehenga_{resolution}_{aspect_ratio}.jpg",
                            mime="image/jpeg"
                        )
                        if description_text:
                            with st.expander("📄 Generation Details"):
                                st.write(description_text)
                        st.success(f"✅ {resolution} resolution image generated successfully!")
                    else:
                        output_placeholder.error("❌ No image was generated. Please try again.")
                        if description_text:
                            st.write("Response text:", description_text)
                        with st.expander("🔍 Debug Info"):
                            st.write(response)

            except Exception as e:
                st.error(f"❌ Error generating image: {str(e)}")
                st.exception(e)
