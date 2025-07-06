import streamlit as st
import requests
from PIL import Image
from io import BytesIO

"""
Streamlit Upload and Generate Image Simulation App
"""

# FastAPI Backend URL (change this if needed)
BACKEND_URL = "http://127.0.0.1:8000"

st.title("Simple Image Upload & Generate Test (Streamlit + FastAPI)")

# Image Uploader in Streamlit
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption='Uploaded Image Preview', use_container_width=True)
    
    if st.button("Generate Image (simply show same image)"):
        # Upload to FastAPI backend
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        try:
            response = requests.post(f"{BACKEND_URL}/upload-image/", files=files)
            response.raise_for_status()
            result = response.json()
            
            file_url = f"{BACKEND_URL}{result['file_url']}"  # Full URL for FastAPI endpoint
            
            st.success("Image uploaded and 'generated'!")
            st.write("Generated Image URL:", file_url)
            
            # Display the generated image
            gen_image_response = requests.get(file_url)
            if gen_image_response.status_code == 200:
                img = Image.open(BytesIO(gen_image_response.content))
                st.image(img, caption='Generated Image (Same as Uploaded)', use_container_width=True)
            else:
                st.error("Error fetching generated image.")
        except Exception as e:
            st.error(f"Error: {e}")