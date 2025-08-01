import streamlit as st
from streamlit_image_comparison import image_comparison
import requests
import os
import cv2
import numpy as np
from PIL import Image
import io

# --- CONFIGURATION ---
BACKEND_URL = "http://localhost:8000"
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
  # --- 1. STATE MANAGEMENT INITIALIZATION ---
  # Initialize the app's stage to control what is displayed.
  if "stage" not in st.session_state:
      st.session_state.stage = "initial"
  if "generated_data" not in st.session_state:
      st.session_state.generated_data = None
  if "similarity_results" not in st.session_state:
      st.session_state.similarity_results = None
  if "image_bytes" not in st.session_state:
      st.session_state.image_bytes = None
  if "selected_type" not in st.session_state:
      st.session_state.selected_type = None

  # --- 2. INPUT FORM ---
  st.header("1. Generate a New Room Design")

  with st.form("generation_form"):
    col1, col2 = st.columns(2)
    with col1:
      uploaded_file = st.file_uploader(
        "Upload an image of your empty room:",
        type=["jpg", "jpeg", "png"]
      )
    with col2:
      room_style = st.selectbox("Select Room Type:", ["Living Room", "Bedroom"])
      design_style = st.selectbox("Select Design Style:", ["Scandinavian", "Modern"])

    # This button submits the form
    submitted = st.form_submit_button("✨ Generate Design & Find Similar Furniture", type="primary")

  # --- 3. PROCESSING LOGIC ---
  # This block runs ONLY when the form is submitted.
  if submitted and uploaded_file:
      st.session_state.stage = "processing" # Update stage to show spinners
      st.session_state.selected_type = None # Reset coordinate selection

      with st.spinner("Generating new design... Please wait, this can take a minute."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        data = {"room_style": room_style, "design_style": design_style}
        try:
          gen_response = requests.post(
            f"{BACKEND_URL}/generated/generate-image/",
            files=files, data=data, timeout=300
          )
          gen_response.raise_for_status()
          st.session_state.generated_data = gen_response.json()
        except requests.exceptions.RequestException as e:
          st.error(f"❌ Failed to generate design: {e}")
          st.session_state.stage = "initial" # Reset stage on error
          st.stop()

      with st.spinner("Detecting objects and finding similar items..."):
        try:
          with open(st.session_state.generated_data["generated_image_path"], "rb") as f:
            st.session_state.image_bytes = f.read()
          
          room_id = st.session_state.generated_data["generated_room_id"]
          sim_response = requests.post(
            f"{BACKEND_URL}/generated/detect-and-find-similar/?generated_room_id={room_id}",
            files={"file": ("generated_image.jpg", st.session_state.image_bytes, "image/jpeg")},
            timeout=180
          )
          sim_response.raise_for_status()
          st.session_state.similarity_results = sim_response.json()
        except requests.exceptions.RequestException as e:
          st.error(f"❌ Could not process furniture detection: {e}")
          st.session_state.stage = "initial" # Reset stage on error
          st.stop()
      
      # Once all processing is done, set the stage to show results
      st.session_state.stage = "results_ready"


  # --- 4. DISPLAY BLOCK ---
  # This block renders the results based on the current app stage.
  # It persists across reruns caused by clicking inner buttons.
  if st.session_state.stage == "results_ready":
    st.success("✅ Process complete! View your results below.")
    st.markdown("---")
    
    # --- Display Image Comparison ---
    st.header("2. Compare Your Original Room vs. AI-Generated Design")
    image_comparison(
      img1=st.session_state.generated_data["original_image_path"],
      img2=st.session_state.generated_data["generated_image_path"],
      label1="Original", label2="Generated", width=700,
    )

    # --- Display Detection and Recommendations ---
    st.header("3. Detection Results & Product Matches")
    if "detected_items" in st.session_state.similarity_results and st.session_state.similarity_results["detected_items"]:
      img_array = np.array(Image.open(io.BytesIO(st.session_state.image_bytes)))
      img_with_boxes = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

      for item in st.session_state.similarity_results["detected_items"]:
        box = item["bounding_box"]
        cv2.rectangle(img_with_boxes, (box["x1"], box["y1"]), (box["x2"], box["y2"]), (34, 139, 34), 2)
        cv2.putText(
          img_with_boxes, item["class_name"].title(), (box["x1"], box["y1"] - 10),
          cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2
        )
      
      st.image(cv2.cvtColor(img_with_boxes, cv2.COLOR_BGR2RGB), caption="Detected Furniture", use_container_width=True)

      st.subheader("Recommended Products")
      matched_items = [item for item in st.session_state.similarity_results["detected_items"] if item["similar_products"]]
      if not matched_items:
        st.warning("Could not find any matching products in the catalog.")
      else:
        num_columns = min(len(matched_items), 3)
        cols = st.columns(num_columns)
        for i, item in enumerate(matched_items):
          with cols[i % num_columns]:
            product = item["similar_products"][0]
            st.image(product['image_url'], caption=f"Similarity: {product['similarity_score']:.2f}")
            st.markdown(f"**{product['product_name']}**")
            st.link_button("🛒 View Product", product['product_url'])
    
    # --- Display Interactive Coordinates ---
    st.markdown("---")
    st.header("4. Interactive Furniture Coordinates")
    try:
      room_id = st.session_state.generated_data["generated_room_id"]
      coord_response = requests.get(f"{BACKEND_URL}/generated/coordinates/{room_id}", timeout=30)
      coord_response.raise_for_status()
      coordinates = coord_response.json()
      
      st.write("Click a furniture type to see its coordinates and location marked with a red circle.")
      unique_types = sorted(list(set(c['type'] for c in coordinates)))
      cols = st.columns(len(unique_types) + 1)

      for i, f_type in enumerate(unique_types):
        with cols[i]:
          if st.button(f_type.title()):
            st.session_state.selected_type = f_type
      with cols[-1]:
        if st.button("Clear Selection"):
          st.session_state.selected_type = None
          
      if st.session_state.selected_type:
        img_for_buttons = np.array(Image.open(io.BytesIO(st.session_state.image_bytes)))
        img_for_buttons = cv2.cvtColor(img_for_buttons, cv2.COLOR_RGB2BGR)
        h, w, _ = img_for_buttons.shape
        selected_type = st.session_state.selected_type
        coords_for_type = [c for c in coordinates if c['type'] == selected_type]
        
        st.write(f"**Coordinates for {selected_type.title()}:**")
        for coord in coords_for_type:
          st.code(f"x: {coord['x_coordinate']:.4f}, y: {coord['y_coordinate']:.4f}")
          center_x = int(coord['x_coordinate'] * w)
          center_y = int(coord['y_coordinate'] * h)
          cv2.circle(img_for_buttons, (center_x, center_y), 20, (255, 0, 0), 3)
        
        st.image(cv2.cvtColor(img_for_buttons, cv2.COLOR_BGR2RGB), caption=f"Showing location(s) for: {selected_type.title()}", use_container_width=True)

    except requests.exceptions.RequestException as e:
      st.error(f"❌ Could not fetch coordinates: {e}")


# ==============================================================================
# TABS 2, 3, 4 (Unchanged)
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
    cols = st.columns(3)
    for idx, room in enumerate(rooms):
      col = cols[idx % 3]
      with col:
        st.subheader(room["generated_room_id"])
        image_url = f"{BACKEND_URL}/generated/view/generated/{os.path.basename(room['generated_image_path'])}"
        st.image(image_url, caption=f"{room['room_style']} - {room['design_style']}", use_container_width=True)
        st.caption(f"Generated on: {room['generated_date']}")

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
      img1=original_url, img2=generated_url,
      label1="Before", label2="After",
    )

with tab4:
  st.header("📚 Furniture Catalog")
  try:
    res = requests.get(f"{BACKEND_URL}/furniture/")
    all_furniture = res.json() if res.status_code == 200 else []
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