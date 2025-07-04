import streamlit as st
import requests
import os
import io
from PIL import Image

# --- Configuration ---
# Assuming your FastAPI app is running locally on port 8000
FASTAPI_BASE_URL = "http://127.0.0.1:8000"

# --- Streamlit App Layout ---
st.set_page_config(layout="wide", page_title="Furniture & Room Design App")

st.title("🛋️ Furniture and Room Design App")

# --- Tabs for navigation ---
tab1, tab2, tab3 = st.tabs(["Upload & Generate Design", "View All Furniture", "Manage Furniture (Admin)"])

# Initialize session state for room_design_id
# This helps persist the ID across reruns of the Streamlit app
if 'current_room_design_id' not in st.session_state:
    st.session_state.current_room_design_id = None

# --- Tab 1: Upload & Generate Design ---
with tab1:
    st.header("Upload Image & Generate Room Design")

    # Fetch furniture items to link the design to
    st.subheader("Select Furniture for Design")
    furniture_items = []
    selected_furniture_id = None
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/get-furniture")
        response.raise_for_status() # Raise an exception for bad status codes
        furniture_items = response.json()

        if furniture_items:
            furniture_options = {f"{item['name']} (ID: {item['id']})": item['id'] for item in furniture_items}
            selected_furniture_display = st.selectbox(
                "Choose a furniture item to associate with this design:",
                list(furniture_options.keys())
            )
            selected_furniture_id = furniture_options[selected_furniture_display]
        else:
            st.warning("No furniture items found. Please add some in the 'Manage Furniture' tab first.")

    except requests.exceptions.ConnectionError:
        st.error(f"Could not connect to FastAPI at {FASTAPI_BASE_URL}. Please ensure the backend is running.")
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching furniture: {e}")

    st.markdown("---")

    if selected_furniture_id:
        st.subheader("Upload Original Room Image")
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

        if uploaded_file is not None:
            st.image(uploaded_file, caption="Original Image Preview", use_container_width=True)

            if st.button("Upload Image"):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    upload_response = requests.post(f"{FASTAPI_BASE_URL}/upload-image/{selected_furniture_id}", files=files)
                    upload_response.raise_for_status()
                    uploaded_design_info = upload_response.json()
                    st.session_state.current_room_design_id = uploaded_design_info['id'] # Store the ID
                    st.success(f"Image uploaded successfully! Design ID: {st.session_state.current_room_design_id}")
                    st.json(uploaded_design_info)

                    # Display the uploaded image from the server
                    original_image_url_parts = uploaded_design_info['original_image_path'].split(os.sep)
                    original_image_url_filename = original_image_url_parts[-1]
                    original_image_url_folder = original_image_url_parts[-2] # Should be 'uploads'
                    
                    st.write("Uploaded Image on Server (Original):")
                    st.image(f"{FASTAPI_BASE_URL}/view-image/{original_image_url_folder}/{original_image_url_filename}", caption="Uploaded Image from Server", use_container_width=True)

                except requests.exceptions.RequestException as e:
                    st.error(f"Error uploading image: {e}")
                    if upload_response and hasattr(upload_response, 'json'):
                        try:
                            error_detail = upload_response.json().get('detail', 'Unknown error')
                            st.error(f"Detail: {error_detail}")
                        except ValueError:
                            st.error(f"Raw response: {upload_response.text}")
                
        st.markdown("---")

        st.subheader("Generate Design (Simulated)")
        
        # Use st.session_state.current_room_design_id to pre-fill the input
        default_id_value = st.session_state.current_room_design_id if st.session_state.current_room_design_id else 1
        current_room_design_id_input = st.number_input(
            "Enter Room Design ID to Generate (or use the one from upload above):",
            min_value=1,
            value=default_id_value,
            key="generate_id_input" # Add a key to prevent potential issues with multiple number inputs
        )

        if st.button("Generate Design"):
            if current_room_design_id_input:
                try:
                    generate_response = requests.post(f"{FASTAPI_BASE_URL}/generate-image/{current_room_design_id_input}")
                    generate_response.raise_for_status()
                    generated_design_info = generate_response.json()
                    st.success("Design generated successfully (simulated)!")
                    st.json(generated_design_info)

                    # Display original and generated images side-by-side
                    st.subheader("Original vs. Generated Design")
                    col1, col2 = st.columns(2)

                    # Display Original Image
                    original_path_parts = generated_design_info['original_image_path'].split(os.sep)
                    original_filename = original_path_parts[-1]
                    original_folder = original_path_parts[-2]
                    original_image_url = f"{FASTAPI_BASE_URL}/view-image/{original_folder}/{original_filename}"
                    
                    with col1:
                        st.image(original_image_url, caption="Original Image", use_container_width=True)

                    # Display Generated Image
                    generated_path_parts = generated_design_info['generated_image_path'].split(os.sep)
                    generated_filename = generated_path_parts[-1]
                    generated_folder = generated_path_parts[-2]
                    generated_image_url = f"{FASTAPI_BASE_URL}/view-image/{generated_folder}/{generated_filename}"
                    
                    with col2:
                        st.image(generated_image_url, caption="Generated Design (Simulated)", use_container_width=True)

                except requests.exceptions.RequestException as e:
                    st.error(f"Error generating design: {e}")
                    if generate_response and hasattr(generate_response, 'json'):
                        try:
                            error_detail = generate_response.json().get('detail', 'Unknown error')
                            st.error(f"Detail: {error_detail}")
                        except ValueError:
                            st.error(f"Raw response: {generate_response.text}")
            else:
                st.warning("Please upload an image first or enter a Room Design ID.")
    else:
        st.info("Please select a furniture item above to proceed with image upload.")

# --- Tab 2: View All Furniture ---
with tab2:
    st.header("All Furniture Items and Room Designs")

    if st.button("Refresh Furniture List"):
        st.cache_data.clear() # Clear cache to fetch fresh data

    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/get-furniture")
        response.raise_for_status()
        all_furniture = response.json()

        if all_furniture:
            for furniture in all_furniture:
                st.subheader(f"🛋️ {furniture['name']} (ID: {furniture['id']})")
                st.write(f"**Style:** {furniture['style']} | **Room:** {furniture['room']} | **Type:** {furniture['type']}")
                st.write(f"**Price:** ${furniture['price']:.2f}")
                
                if furniture['imageLink']:
                    st.image(furniture['imageLink'], caption="Furniture Image (External Link)", width=200)
                if furniture['purchaseLink']:
                    st.write(f"[Purchase Link]({furniture['purchaseLink']})")

                # Fetch and display associated room designs
                st.markdown("##### Associated Room Designs:")
                # To properly display room designs linked to furniture, you'd ideally add a new endpoint
                # in your FastAPI, e.g., GET /furniture/{furniture_id}/room-designs
                
                # For now, let's just show a placeholder or filter all designs if available (less efficient)
                # If you implement an endpoint:
                # try:
                #     room_designs_response = requests.get(f"{FASTAPI_BASE_URL}/furniture/{furniture['id']}/room-designs")
                #     room_designs_response.raise_for_status()
                #     room_designs_for_furniture = room_designs_response.json()
                #     if room_designs_for_furniture:
                #         for design in room_designs_for_furniture:
                #             st.write(f"Design ID: {design['id']} (Style: {design['design_style']})")
                #             col_orig, col_gen = st.columns(2)
                #             with col_orig:
                #                 st.image(f"{FASTAPI_BASE_URL}/view-image/uploads/{os.path.basename(design['original_image_path'])}", caption="Original", width=150)
                #             with col_gen:
                #                 st.image(f"{FASTAPI_BASE_URL}/view-image/generated/{os.path.basename(design['generated_image_path'])}", caption="Generated", width=150)
                #     else:
                #         st.info("No room designs for this furniture yet.")
                # except requests.exceptions.RequestException:
                #     st.warning("Could not fetch room designs for this furniture.")
                st.info("Room designs for this furniture would appear here if a dedicated API endpoint existed.")

                st.markdown("---")
        else:
            st.info("No furniture items added yet.")

    except requests.exceptions.ConnectionError:
        st.error(f"Could not connect to FastAPI at {FASTAPI_BASE_URL}. Please ensure the backend is running.")
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching furniture: {e}")

# --- Tab 3: Manage Furniture (Admin) ---
with tab3:
    st.header("Manage Furniture Items")
    st.subheader("Add New Furniture")

    with st.form("add_furniture_form"):
        new_style = st.text_input("Style")
        new_room = st.text_input("Room")
        new_name = st.text_input("Name")
        new_type = st.text_input("Type")
        new_price = st.number_input("Price", min_value=0.0, format="%.2f")
        new_image_link = st.text_input("Image Link (URL)")
        new_purchase_link = st.text_input("Purchase Link (URL)")
        
        add_submitted = st.form_submit_button("Add Furniture")

        if add_submitted:
            furniture_data = {
                "style": new_style,
                "room": new_room,
                "name": new_name,
                "type": new_type,
                "price": new_price,
                "imageLink": new_image_link,
                "purchaseLink": new_purchase_link
            }
            try:
                response = requests.post(f"{FASTAPI_BASE_URL}/furniture/", json=furniture_data)
                response.raise_for_status()
                st.success("Furniture added successfully!")
                st.json(response.json())
            except requests.exceptions.RequestException as e:
                st.error(f"Error adding furniture: {e}")
                if response and hasattr(response, 'json'):
                    try:
                        error_detail = response.json().get('detail', 'Unknown error')
                        st.error(f"Detail: {error_detail}")
                    except ValueError:
                        st.error(f"Raw response: {response.text}")

    st.markdown("---")
    st.subheader("View All Existing Furniture")
    
    if st.button("Load Existing Furniture (Admin View)"):
        try:
            response = requests.get(f"{FASTAPI_BASE_URL}/get-furniture")
            response.raise_for_status()
            existing_furniture = response.json()
            if existing_furniture:
                for item in existing_furniture:
                    st.write(f"**ID:** {item['id']}")
                    st.write(f"**Name:** {item['name']}")
                    st.write(f"**Style:** {item['style']}")
                    st.write(f"**Room:** {item['room']}")
                    st.write(f"**Type:** {item['type']}")
                    st.write(f"**Price:** ${item['price']:.2f}")
                    st.write(f"**Image Link:** {item['imageLink']}")
                    st.write(f"**Purchase Link:** {item['purchaseLink']}")
                    st.markdown("---")
            else:
                st.info("No furniture items found.")
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching existing furniture: {e}")