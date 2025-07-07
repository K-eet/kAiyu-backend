import streamlit as st
from streamlit_image_comparison import image_comparison
import requests
import os

BACKEND_URL = "http://localhost:8080"

st.set_page_config(page_title="AI Interior Design App", layout="wide")

# --- Tab Setup ---
tab1, tab2, tab3, tab4 = st.tabs(
  [
    "🛠️ Upload & Generate Coordinates", 
    "🛋️ Furniture Viewer", 
    "📸 Gallery",
    "🖼️ Before vs After",
  ])

# ========== TAB 1 ==========
with tab1:
  st.header("Upload Empty Room and Input Furniture Coordinates")

  uploaded_file = st.file_uploader("Upload Room Image", type=["jpg", "jpeg", "png"])
  room_style = st.selectbox("Room Type", ["Living Room", "Bedroom", "Kitchen"])
  design_style = st.selectbox("Design Style", ["Scandinavian", "Modern", "Minimalist"])

  if st.button("Upload & Generate Image"):
    if uploaded_file:
      files = {"file": uploaded_file.getvalue()}
      data = {
        "room_style": room_style,
        "design_style": design_style,
      }
      response = requests.post(f"{BACKEND_URL}/generated/generate-image/", files={"file": uploaded_file}, data=data)

      if response.status_code == 200:
        result = response.json()
        st.success("Image generated successfully!")
        st.image(result["generated_image_path"], caption="Generated Image", use_container_width=True)
        generated_room_id = result["generated_room_id"]
        st.session_state["generated_room_id"] = generated_room_id
      else:
        st.error(f"Failed: {response.json().get('detail', 'Unknown error')}")
    else:
      st.warning("Please upload a room image.")

  # Manual coordinate entry
  st.markdown("### Enter Furniture Hotspots (x, y)")

  generated_room_id = st.session_state.get("generated_room_id", None)
  if generated_room_id:
    coords = []
    num = st.number_input("Number of furniture items to label", min_value=1, max_value=10, value=1)

    for i in range(num):
      st.subheader(f"Furniture {i+1}")
      fid = st.text_input(f"Furniture ID {i+1}", key=f"fid{i}")
      x = st.slider(f"X Coordinate {i+1}", 0.0, 1.0, 0.5, key=f"x{i}")
      y = st.slider(f"Y Coordinate {i+1}", 0.0, 1.0, 0.5, key=f"y{i}")
      coords.append({
        "furniture_id": fid,
        "x_coordinate": x,
        "y_coordinate": y
      })

    if st.button("Submit Coordinates"):
      payload = {
        "generated_room_id": generated_room_id,
        "coordinates": coords
      }
      response = requests.post(f"{BACKEND_URL}/generated/coordinates/batch", json=payload)
      if response.status_code == 200:
        st.success("Furniture coordinates saved!")
      else:
        st.error(f"Error: {response.json().get('detail')}")

    # Optional simulated AI generation
    if st.button("Simulate AI-generated coordinates"):
      response = requests.post(f"{BACKEND_URL}/generated/coordinates/auto-generate?generated_room_id={generated_room_id}")
      if response.status_code == 200:
        st.success("Simulated AI coordinates inserted.")
      else:
        st.error(response.json().get("detail"))

  else:
    st.info("Please upload and generate an image first.")

# ========== TAB 2 ==========
with tab2:
  st.header("Furniture List")

  # Filter controls
  col1, col2, col3 = st.columns(3)
  with col1:
    selected_room = st.selectbox("Filter by Room", ["", "Living Room", "Bedroom", "Kitchen"])
  with col2:
    selected_style = st.selectbox("Filter by Style", ["", "Scandinavian", "Modern", "Minimalist"])
  with col3:
    selected_type = st.selectbox("Filter by Type", ["", "Chair", "Table", "Bed", "Cabinet", "Sofa"])

  furniture_items = []

  # Construct filter logic
  try:
    if selected_type and not (selected_room or selected_style):
      # Filter by type only
      res = requests.get(f"{BACKEND_URL}/furniture/filter-type", params={"type": selected_type})
      if res.status_code == 200:
        furniture_items = res.json()
    elif selected_room or selected_style:
      # Filter by room and/or style
      res = requests.get(f"{BACKEND_URL}/furniture/filter", params={
        "room": selected_room if selected_room else None,
        "style": selected_style if selected_style else None
      })
      if res.status_code == 200:
        furniture_items = res.json()
    else:
      # No filter, get all
      res = requests.get(f"{BACKEND_URL}/furniture/")
      if res.status_code == 200:
        furniture_items = res.json()
  except Exception as e:
    st.error(f"Failed to fetch furniture: {str(e)}")

  # Display furniture list
  if furniture_items:
    for f in furniture_items:
      with st.container():
        st.markdown(f"### {f['name']} (ID: {f['furniture_id']})")
        if f["image_link"]:
          st.image(f["image_link"], width=200)
        st.write(f"Room: {f['room']} | Style: {f['style']} | Type: {f['type']}")
        st.write(f"Price: RM{f['price']} | [Buy Now]({f['purchase_link']})")
        st.markdown("---")
  else:
    st.info("No furniture items found for the selected filter(s).")

# ========== TAB 3 ==========       
with tab3:
  st.header("📸 Gallery - Previously Generated Rooms")

  try:
    res = requests.get(f"{BACKEND_URL}/generated/gallery")
    if res.status_code == 200:
      rooms = res.json()
    else:
      st.error("Failed to fetch generated rooms")
      rooms = []
  except Exception as e:
    st.error(f"Error fetching gallery: {e}")
    rooms = []

  if not rooms:
    st.info("No generated rooms found.")
  else:
    # Display 3 images per row
    cols = st.columns(3)
    for idx, room in enumerate(rooms):
      col = cols[idx % 3] # pick one of the 3 columns
      with col:
        st.subheader(room["generated_room_id"])
        filename = os.path.basename(room["generated_image_path"])
        image_url = f"{BACKEND_URL}/generated/view/generated/{filename}"
        st.image(image_url, caption=f"{room['room_style']} - {room['design_style']}", use_container_width=True)
        st.caption(f"Generated on: {room['generated_date']}")

      # Create a new row after every 3 images
      if (idx + 1) % 3 == 0 and (idx + 1) != len(rooms):
        cols = st.columns(3)

# ========== TAB 4 ==========     
with tab4:
  st.header("🖼️ Before vs After - Image Comparison")

  try:
    res = requests.get(f"{BACKEND_URL}/generated/gallery")
    if res.status_code == 200:
      rooms = res.json()
    else:
      st.error("Failed to fetch generated rooms")
      rooms = []
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

    original_filename = os.path.basename(selected_room["original_image_path"])
    generated_filename = os.path.basename(selected_room["generated_image_path"])
    
    original_url = f"{BACKEND_URL}/generated/view/uploads/{original_filename}"
    generated_url = f"{BACKEND_URL}/generated/view/generated/{generated_filename}"

    st.subheader(f"🛋️ Room Style: {selected_room['room_style']} | 🎨 Design: {selected_room['design_style']}")
    image_comparison(
      img1=original_url,
      img2=generated_url,
      label1="Before",
      label2="After",
    )