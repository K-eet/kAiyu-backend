import streamlit as st
from streamlit_image_comparison import image_comparison
import requests
import os
import cv2
import numpy as np
from PIL import Image
import io

# --- CONFIGURATION ---
# Use the correct port for your backend (e.g., 8080 as per your last request)
BACKEND_URL = "http://localhost:8080" 
st.set_page_config(page_title="AI Interior Design", layout="wide")

# --- UI SETUP ---
st.title("🏠 AI Interior Design Web App")

tab1, tab2, tab3, tab4 = st.tabs([
    "🛋️ Design & Match Furniture",
    "📸 Gallery",
    "🖼️ Before vs. After",
    "📚 Furniture Catalog"
])

# ==============================================================================
# TAB 1: DESIGN & MATCH FURNITURE
# ==============================================================================
with tab1:
    st.header("1. Generate a New Room Design")
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader(
            "Upload an image of your empty room:", 
            type=["jpg", "jpeg", "png"]
        )
    
    with col2:
        room_style = st.selectbox("Select Room Type:", ["Living Room", "Bedroom"])
        design_style = st.selectbox("Select Design Style:", ["Scandinavian", "Modern"])

    if st.button("✨ Generate Design & Find Similar Furniture", type="primary"):
        if uploaded_file:
            with st.spinner("Generating new design... Please wait."):
                # STEP 1: Generate the new room design
                # files = {"file": uploaded_file.getvalue()}
                files = {
                        "file": (
                            uploaded_file.name,      # Provides the filename (e.g., "my_room.jpg")
                            uploaded_file.getvalue(),  # Provides the raw file bytes
                            uploaded_file.type         # Provides the MIME type (e.g., "image/jpeg")
                        )
                    }
                data = {"room_style": room_style, "design_style": design_style}
                
                try:
                    gen_response = requests.post(
                        f"{BACKEND_URL}/generated/generate-image/",
                        files=files,
                        data=data,
                        timeout=300 # Increased timeout for model generation
                    )
                    gen_response.raise_for_status()
                    generated_data = gen_response.json()
                    st.success("✅ Design generated successfully!")
                    
                    # Store generated image path to pass to the next step
                    st.session_state['generated_image_path'] = generated_data["generated_image_path"]

                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Failed to generate design: {e}")
                    st.stop()

            # Display the before-and-after comparison
            st.header("2. Compare Your Original Room vs. AI-Generated Design")
            image_comparison(
                img1=generated_data["original_image_path"],
                img2=generated_data["generated_image_path"],
                label1="Original",
                label2="Generated",
                width=700,
            )

            st.header("3. Detected Furniture & Similar Products")
            with st.spinner("Detecting objects and finding similar items..."):
                # STEP 2: Send the generated image for detection and similarity search
                try:
                    # We need to read the generated image file to send it
                    with open(st.session_state['generated_image_path'], "rb") as f:
                        image_bytes = f.read()

                    # sim_response = requests.post(
                    #     f"{BACKEND_URL}/coordinates/detect-and-find-similar/",
                    #     files={"file": ("generated_image.jpg", image_bytes, "image/jpeg")},
                    #     timeout=180
                    # )

                    sim_response = requests.post(
                        f"{BACKEND_URL}/generated/detect-and-find-similar/", # <- Correct path with prefix
                        files={"file": ("generated_image.jpg", image_bytes, "image/jpeg")},
                        timeout=180
                    )
                    sim_response.raise_for_status()
                    similarity_results = sim_response.json()
                    st.success("✅ Found matching furniture from the catalog!")

                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Could not find similar furniture: {e}")
                    st.stop()
                
                # STEP 3: Display the results
                if "detected_items" in similarity_results and similarity_results["detected_items"]:
                    # Load the generated image to draw bounding boxes on it
                    img_array = np.array(Image.open(io.BytesIO(image_bytes)))
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                    for item in similarity_results["detected_items"]:
                        box = item["bounding_box"]
                        x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
                        # Draw rectangle and label
                        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (36, 255, 12), 2)
                        cv2.putText(
                            img_bgr,
                            item["class_name"],
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2
                        )
                    
                    st.image(
                        cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), 
                        caption="Detected Furniture", 
                        use_container_width=True
                    )

                    # Display each detected item and its similar products
                    for item in similarity_results["detected_items"]:
                        with st.expander(f"✨ Detected: **{item['class_name'].capitalize()}** (Confidence: {item['confidence']:.2f})", expanded=True):
                            if item["similar_products"]:
                                for product in item["similar_products"]:
                                    col1, col2 = st.columns([1, 2])
                                    with col1:
                                        st.image(product['image_url'], caption=f"Catalog Match (Score: {product['similarity_score']:.2f})")
                                    with col2:
                                        st.markdown(f"#### {product['product_name']}")
                                        st.markdown(f"**Similarity Score:** `{product['similarity_score']:.3f}`")
                                        st.markdown(f"[🛒 View & Purchase]({product['product_url']})", unsafe_allow_html=True)
                            else:
                                st.warning(f"No similar items found in the catalog for **{item['class_name']}**.")
                else:
                    st.info("No furniture was detected in the generated image.")
        else:
            st.warning("⚠️ Please upload a room image first.")

# ==============================================================================
# TAB 2: GALLERY
# ==============================================================================
with tab2:
    st.header("📸 Gallery - Previously Generated Rooms")
    
    try:
        res = requests.get(f"{BACKEND_URL}/generated/gallery")
        rooms = res.json() if res.status_code == 200 else []
    except Exception as e:
        st.error(f"Error fetching gallery: {e}")
        rooms = []

    if not rooms:
        st.info("No generated rooms found.")
    else:
        # Create columns dynamically
        cols = st.columns(3)
        for idx, room in enumerate(rooms):
            col = cols[idx % 3]
            with col:
                st.subheader(room["generated_room_id"])
                # The backend should serve static files from the correct path
                image_url = f"{BACKEND_URL}/generated/view/generated/{os.path.basename(room['generated_image_path'])}"
                st.image(image_url, caption=f"{room['room_style']} - {room['design_style']}", use_container_width=True)
                st.caption(f"Generated on: {room['generated_date']}")

# ==============================================================================
# TAB 3: BEFORE VS. AFTER
# ==============================================================================
with tab3:
    st.header("🖼️ Before vs After - Image Comparison")

    try:
        res = requests.get(f"{BACKEND_URL}/generated/gallery")
        rooms = res.json() if res.status_code == 200 else []
    except Exception as e:
        st.error(f"Error fetching gallery: {e}")
        rooms = []

    if not rooms:
        st.info("No generated rooms to compare.")
    else:
        selected_room = st.selectbox(
            "Select a generated room to compare:",
            options=rooms,
            format_func=lambda r: f"{r['generated_room_id']} ({r['room_style']} - {r['design_style']})"
        )

        original_url = f"{BACKEND_URL}/generated/view/uploads/{os.path.basename(selected_room['original_image_path'])}"
        generated_url = f"{BACKEND_URL}/generated/view/generated/{os.path.basename(selected_room['generated_image_path'])}"

        st.subheader(f"🛋️ Room Style: {selected_room['room_style']} | 🎨 Design: {selected_room['design_style']}")
        image_comparison(
            img1=original_url,
            img2=generated_url,
            label1="Before",
            label2="After",
        )

# ==============================================================================
# TAB 4: FURNITURE CATALOG
# ==============================================================================
with tab4:
    st.header("📚 Furniture Catalog")

    # Fetch all furniture to populate filters
    try:
        res = requests.get(f"{BACKEND_URL}/furniture/")
        all_furniture = res.json() if res.status_code == 200 else []
        
        # Get unique values for filters
        room_options = ["All"] + sorted(list(set(item['room'] for item in all_furniture)))
        style_options = ["All"] + sorted(list(set(item['style'] for item in all_furniture)))
        type_options = ["All"] + sorted(list(set(item['type'] for item in all_furniture)))

    except Exception as e:
        st.error(f"Failed to fetch furniture catalog: {e}")
        all_furniture = []
        room_options, style_options, type_options = ["All"], ["All"], ["All"]

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_room = st.selectbox("Filter by Room", room_options)
    with col2:
        selected_style = st.selectbox("Filter by Style", style_options)
    with col3:
        selected_type = st.selectbox("Filter by Type", type_options)

    # Filter the displayed items based on selection
    filtered_items = all_furniture
    if selected_room != "All":
        filtered_items = [item for item in filtered_items if item['room'] == selected_room]
    if selected_style != "All":
        filtered_items = [item for item in filtered_items if item['style'] == selected_style]
    if selected_type != "All":
        filtered_items = [item for item in filtered_items if item['type'] == selected_type]

    if filtered_items:
        cols = st.columns(4)
        for i, item in enumerate(filtered_items):
            with cols[i % 4]:
                st.image(item["image_link"], use_container_width=True, caption=item["name"])
                st.markdown(f"**Type:** {item['type']}")
                st.markdown(f"**Price:** RM {item['price']:.2f}")
                if item["purchase_link"]:
                    st.link_button("🛒 Buy Now", item["purchase_link"])
    else:
        st.info("No furniture items found for the selected filter(s).")