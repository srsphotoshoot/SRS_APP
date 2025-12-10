import streamlit as st
from PIL import Image
from io import BytesIO
import base64
import google.generativeai as genai

# Load Gemini API key from Streamlit secrets
GEMINI_API_KEY = st.secrets.get("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    st.error("⚠️ Google API key not found in Streamlit secrets!")
    st.stop()

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Your working model name
MODEL_NAME = "gemini-3-pro-image-preview"
model = genai.GenerativeModel(MODEL_NAME)


VIRTUAL_TRYON_PROMPT = """Generate a photorealistic image of a professional fashion model wearing this EXACT lehenga outfit.
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


st.set_page_config(page_title="Virtual Lehenga Try-On", page_icon="👗", layout="wide")

st.title("👗 Virtual Lehenga Try-On")
st.markdown("Upload your lehenga image and generate a professional model try-on image")


col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Lehenga Image")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a lehenga image",
        type=["jpg", "jpeg", "png"],
        help="Upload a clear image of the lehenga outfit"
    )
    
    # Display uploaded image
    if uploaded_file:
        input_image = Image.open(uploaded_file).convert("RGB")
        st.image(input_image, caption="Input Lehenga", use_container_width=True)
        
        # Optional: Show the prompt being used
        with st.expander("📝 View Generation Prompt"):
            st.text_area("Prompt", VIRTUAL_TRYON_PROMPT, height=300, disabled=True)
    
    # Generate button
    generate_btn = st.button("🎨 Generate Model Image", type="primary", use_container_width=True)

with col2:
    st.subheader("✨ Generated Result")
    
    # Placeholder for output
    output_placeholder = st.empty()
    
    if not uploaded_file:
        output_placeholder.info("👈 Upload a lehenga image to get started")

# ----------------- Generation Logic -----------------
if generate_btn:
    if not uploaded_file:
        st.error("Please upload a lehenga image first!")
    else:
        with st.spinner("🎨 Generating model image... This may take a moment..."):
            try:
                # Prepare content for the model
                contents = [
                    VIRTUAL_TRYON_PROMPT,
                    input_image
                ]
                
                # Generate content
                response = model.generate_content(contents)
                # Debug - Add temporarily
                st.write("**Checking response parts:**")
                if response.candidates:
                    for i, candidate in enumerate(response.candidates):
                      st.write(f"Candidate {i}:")
                if candidate.content and candidate.content.parts:
                 for j, part in enumerate(candidate.content.parts):
                    st.write(f"  Part {j} type: {type(part)}")
                    st.write(f"  Part {j} attributes: {[attr for attr in dir(part) if not attr.startswith('_')]}")
                
                # Extract generated image and description
                description_text = ""
                output_image_data = None
                
                # Try to get text first
                try:
                    if hasattr(response, 'text'):
                        description_text = response.text
                except:
                    pass
                
                # Check candidates for parts
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            content = candidate.content
                            if hasattr(content, 'parts') and content.parts:
                                for part in content.parts:
                                    # Try to get text from part
                                    try:
                                        if hasattr(part, 'text'):
                                            part_text = part.text
                                            if part_text:
                                                description_text += part_text
                                    except:
                                        pass
                                    
                                    # Try to get image data from inline_data
                                    try:
                                        if hasattr(part, 'inline_data'):
                                            inline = part.inline_data
                                            if hasattr(inline, 'data'):
                                                img_data = inline.data
                                                # Handle both bytes and base64 string
                                                if isinstance(img_data, bytes):
                                                    output_image_data = img_data
                                                elif isinstance(img_data, str):
                                                    output_image_data = base64.b64decode(img_data)
                                    except Exception as e:
                                        st.write(f"Could not extract inline_data: {e}")
                                    
                                    # Try blob as fallback
                                    try:
                                        if not output_image_data and hasattr(part, 'blob'):
                                            blob = part.blob
                                            if hasattr(blob, 'data'):
                                                output_image_data = blob.data
                                    except:
                                        pass
                
                # Display results
                with col2:
                    if output_image_data:
                        # Show generated image
                        img_bytes = BytesIO(output_image_data)
                        generated_image = Image.open(img_bytes)
                        
                        output_placeholder.image(
                            generated_image,
                            caption="Generated Model Image",
                            use_container_width=True
                        )
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Image",
                            data=output_image_data,
                            file_name="lehenga_model_tryon.jpg",
                            mime="image/jpeg",
                            use_container_width=True
                        )
                        
                        # Show description if available
                        if description_text:
                            with st.expander("📄 Generation Details"):
                                st.write(description_text)
                        
                        st.success("✅ Image generated successfully!")
                    
                    else:
                        output_placeholder.error("❌ No image was generated. Please try again.")
                        if description_text:
                            st.write("Response received:", description_text)
                
            except Exception as e:
                st.error(f"❌ Error generating image: {str(e)}")
                st.info("Please check your API key and model access.")


st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>💡 <b>Tip:</b> Use high-quality, well-lit images of lehengas for best results</p>
    <p>🔧 Using model: <code>gemini-3-pro-image-preview</code></p>
</div>
""", unsafe_allow_html=True)