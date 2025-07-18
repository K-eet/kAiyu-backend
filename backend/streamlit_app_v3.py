import streamlit as st
from streamlit_image_comparison import image_comparison
import requests
import os
import cv2
import numpy as np

BACKEND_URL = "http://localhost:8080"

st.set_page_config(page_title="AI Interior Design App", layout="wide")

st.title("🏠 AI Interior Design Web App")

# === Tab Setup ===
tab1, tab2, tab3, tab4 = st.tabs([
  "🧠 Upload & Generate + Object Detection",
  "📸 Gallery",
  "🖼️ Before vs After",
  "🛋️ Furniture Catalog"
])

with tab1:
  st.header("📤 Upload Empty Room and Auto-Detect Furniture Hotspots")

  uploaded_file = st.file_uploader("Upload Room Image", type=["jpg", "jpeg", "png"])
  room_style = st.selectbox("Room Type", ["Living Room", "Bedroom"])
  design_style = st.selectbox("Design Style", ["Scandinavian", "Modern"])

  if st.button("Upload & Generate + Object Detection"):
    if uploaded_file:
      files = {"file": uploaded_file.getvalue()}
      data = {"room_style": room_style, "design_style": design_style}
      response = requests.post(
        f"{BACKEND_URL}/generated/generate-image/",
        files={"file": uploaded_file},
        data=data
      )
      if response.status_code == 200:
        result = response.json()
        st.success("✅ Image generated successfully!")
        st.session_state["generated_room_id"] = result["generated_room_id"]

        with st.expander("🖼️ View Before & After", expanded=True):
          image_comparison(
            img1=result["original_image_path"],
            img2=result["generated_image_path"],
            label1="Original",
            label2="Generated",
            width=700,
          )

        detect_res = requests.post(
          f"{BACKEND_URL}/generated/object-detection?generated_room_id={result['generated_room_id']}"
        )

        if detect_res.status_code == 200:
          detected_coords = detect_res.json()
          st.success("✅ Furniture detected and coordinates saved!")

          img_url = f"{BACKEND_URL}/generated/view/generated/{os.path.basename(result['generated_image_path'])}"
          img_array = cv2.imdecode(
            np.frombuffer(requests.get(img_url).content, np.uint8), cv2.IMREAD_COLOR
          )

          height, width, _ = img_array.shape

          for item in detected_coords:
            x_center = int(item["x_coordinate"] * width)
            y_center = int(item["y_coordinate"] * height)
            w, h = 50, 50
            top_left = (x_center - w // 2, y_center - h // 2)
            bottom_right = (x_center + w // 2, y_center + h // 2)
            cv2.rectangle(img_array, top_left, bottom_right, (0, 255, 0), 2)
            cv2.circle(img_array, (x_center, y_center), 6, (0, 255, 0), -1)
            cv2.putText(img_array, item["type"], (x_center + 5, y_center - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

          st.image(cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB), caption="Detected Furniture Hotspots", use_container_width=True)

          st.markdown("### 🪑 Detected Furniture Hotspots")
          for idx, item in enumerate(detected_coords):
            st.write(f"**Furniture {idx + 1}:**")
            st.write(f"Type: {item['type']}")
            st.write(f"Furniture ID: {item['furniture_id']}")
            st.write(f"Coordinates (Normalized): ({item['x_coordinate']}, {item['y_coordinate']})")
            st.write("---")
        else:
          st.warning(f"⚠️ Object detection failed: {detect_res.status_code} {detect_res.text}")
      else:
        st.error(f"❌ Failed: {response.status_code} {response.text}")
    else:
      st.warning("⚠️ Please upload a room image first.")


# ========== TAB 2 ==========
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
        filename = os.path.basename(room["generated_image_path"])
        image_url = f"{BACKEND_URL}/generated/view/generated/{filename}"
        st.image(image_url, caption=f"{room['room_style']} - {room['design_style']}", use_container_width=True)
        st.caption(f"Generated on: {room['generated_date']}")

      if (idx + 1) % 3 == 0 and (idx + 1) != len(rooms):
        cols = st.columns(3)


# ========== TAB 3 ==========
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


# ========== TAB 4 ==========
with tab4:
  st.header("🛋️ Furniture Catalog")

  col1, col2, col3 = st.columns(3)
  with col1:
    selected_room = st.selectbox("Filter by Room", ["", "Living Room", "Bedroom", "Kitchen"])
  with col2:
    selected_style = st.selectbox("Filter by Style", ["", "Scandinavian", "Modern", "Minimalist"])
  with col3:
    selected_type = st.selectbox("Filter by Type", ["", "Chair", "Table", "Bed", "Cabinet", "Sofa"])

  furniture_items = []

  try:
    if selected_type and not (selected_room or selected_style):
      res = requests.get(f"{BACKEND_URL}/furniture/filter-type", params={"type": selected_type})
    elif selected_room or selected_style:
      res = requests.get(f"{BACKEND_URL}/furniture/filter", params={
        "room": selected_room if selected_room else None,
        "style": selected_style if selected_style else None
      })
    else:
      res = requests.get(f"{BACKEND_URL}/furniture/")

    furniture_items = res.json() if res.status_code == 200 else []
  except Exception as e:
    st.error(f"Failed to fetch furniture: {str(e)}")

  if furniture_items:
    for i in range(0, len(furniture_items), 3):
      cols = st.columns(3)
      for j, item in enumerate(furniture_items[i:i+3]):
        with cols[j]:
          st.image(item["image_link"], use_container_width=True, caption=item["name"])
          st.markdown(f"**ID:** {item['furniture_id']}")
          st.markdown(f"**Room:** {item['room']}")
          st.markdown(f"**Style:** {item['style']}")
          st.markdown(f"**Type:** {item['type']}")
          st.markdown(f"**Price:** RM{item['price']}")
          if item["purchase_link"]:
            st.markdown(f"[🛒 Buy Now]({item['purchase_link']})", unsafe_allow_html=True)
  else:
    st.info("No furniture items found for the selected filter(s).")
