import os
import pandas as pd
import numpy as np
import torch
from torchvision import models, transforms
from PIL import Image
import requests
from io import BytesIO
from sklearn.metrics.pairwise import cosine_similarity
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimilarityService:
  def __init__(self):
    self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    self.feature_extractor = self._load_feature_extractor()
    self.preprocess = self._get_preprocessor()
    self.product_catalog_df = None
    self.catalog_embeddings = None

  def _load_feature_extractor(self):
    """Loads the pre-trained ResNet50 model for feature extraction."""
    logger.info("Loading feature extractor model...")
    model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    model = torch.nn.Sequential(*(list(model.children())[:-1]))
    model.eval()
    model.to(self.device)
    logger.info(f"Feature extractor model loaded and moved to {self.device}.")
    return model

  def _get_preprocessor(self):
    """Returns the image transformation pipeline."""
    return transforms.Compose([
      transforms.Resize(256),
      transforms.CenterCrop(224),
      transforms.ToTensor(),
      transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

  def load_and_process_catalog(self, catalog_path: str):
    """Loads the product catalog from a local CSV and computes embeddings."""
    logger.info(f"Loading and processing product catalog from local file: {catalog_path}...")
    try:
      df = pd.read_csv(catalog_path)
      catalog_records = []
      for _, row in df.iterrows():
        try:
          response = requests.get(row['image_link'], timeout=10)
          response.raise_for_status()
          pil_image = Image.open(BytesIO(response.content)).convert("RGB")

          input_tensor = self.preprocess(pil_image)
          input_batch = input_tensor.unsqueeze(0).to(self.device)

          with torch.no_grad():
            embedding = self.feature_extractor(input_batch).squeeze().cpu().numpy()

          catalog_records.append({
            'product_id': row['id'],
            'product_name': row['name'],
            'product_url': row['purchase_link'],
            'category': row['type'],
            'image_url': row['image_link'],
            'image_embedding': embedding
          })
        except Exception as e:
          logger.error(f"Error processing image for '{row['name']}': {e}")
      
      self.product_catalog_df = pd.DataFrame(catalog_records)
      if not self.product_catalog_df.empty:
        self.catalog_embeddings = np.vstack(self.product_catalog_df['image_embedding'].values)
        logger.info(f"Product catalog created with {len(self.product_catalog_df)} items.")
      else:
        logger.warning("Product catalog is empty after processing.")
    except Exception as e:
      logger.error(f"Failed to load or process catalog from file '{catalog_path}': {e}")

  def find_similar_items(self, cropped_image: Image.Image, class_name: str, top_n: int = 1):
    """Finds the most similar items in the catalog for a given cropped image."""
    if self.product_catalog_df is None or self.product_catalog_df.empty:
      return []

    input_tensor = self.preprocess(cropped_image)
    input_batch = input_tensor.unsqueeze(0).to(self.device)
    with torch.no_grad():
      query_embedding = self.feature_extractor(input_batch).squeeze().cpu().numpy()

    # **THIS IS THE FIX from your Colab logic**
    # It makes the filtering robust to case and whitespace differences.
    relevant_catalog_df = self.product_catalog_df[
      self.product_catalog_df['category'].str.strip().str.lower() == class_name.strip().lower()
    ]
    
    if relevant_catalog_df.empty:
      logger.warning(f"No items found in catalog for category: '{class_name}'")
      return []

    relevant_embeddings = np.vstack(relevant_catalog_df['image_embedding'].values)
    similarities = cosine_similarity(query_embedding.reshape(1, -1), relevant_embeddings)[0]
    
    # This part is also from your Colab: find the top N recommendations
    num_recommendations = 1
    top_indices = np.argsort(similarities)[::-1][:num_recommendations]
    
    results = []
    for idx in top_indices:
      product_info = relevant_catalog_df.iloc[idx]
      results.append({
        "product_name": product_info['product_name'],
        "product_url": product_info['product_url'],
        "similarity_score": float(similarities[idx]),
        "image_url": product_info['image_url']
      })
    
    return results

# Instantiate the service
similarity_service = SimilarityService()

# import os
# import pandas as pd
# import numpy as np
# import torch
# from torchvision import models, transforms
# from PIL import Image
# import requests
# from io import BytesIO
# from sklearn.metrics.pairwise import cosine_similarity
# import logging

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class SimilarityService:
#     def __init__(self):
#         self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#         self.feature_extractor = self._load_feature_extractor()
#         self.preprocess = self._get_preprocessor()
#         self.product_catalog_df = None
#         self.catalog_embeddings = None

#     def _load_feature_extractor(self):
#         """Loads the pre-trained ResNet50 model for feature extraction."""
#         logger.info("Loading feature extractor model...")
#         model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
#         model = torch.nn.Sequential(*(list(model.children())[:-1]))
#         model.eval()
#         model.to(self.device)
#         logger.info(f"Feature extractor model loaded and moved to {self.device}.")
#         return model

#     def _get_preprocessor(self):
#         """Returns the image transformation pipeline."""
#         return transforms.Compose([
#             transforms.Resize(256),
#             transforms.CenterCrop(224),
#             transforms.ToTensor(),
#             transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
#         ])

#     def load_and_process_catalog(self, catalog_path: str):
#         """Loads the product catalog from a local CSV and computes embeddings."""
#         logger.info(f"Loading and processing product catalog from local file: {catalog_path}...")
#         try:
#             df = pd.read_csv(catalog_path)
#             catalog_records = []
#             for _, row in df.iterrows():
#                 try:
#                     response = requests.get(row['image_link'], timeout=10)
#                     response.raise_for_status()
#                     pil_image = Image.open(BytesIO(response.content)).convert("RGB")

#                     input_tensor = self.preprocess(pil_image)
#                     input_batch = input_tensor.unsqueeze(0).to(self.device)

#                     with torch.no_grad():
#                         embedding = self.feature_extractor(input_batch).squeeze().cpu().numpy()

#                     catalog_records.append({
#                         'product_id': row['id'],
#                         'product_name': row['name'],
#                         'product_url': row['purchase_link'],
#                         'category': row['type'],
#                         'image_url': row['image_link'],
#                         'image_embedding': embedding
#                     })
#                 except Exception as e:
#                     logger.error(f"Error processing image for '{row['name']}': {e}")
            
#             self.product_catalog_df = pd.DataFrame(catalog_records)
#             if not self.product_catalog_df.empty:
#                 self.catalog_embeddings = np.vstack(self.product_catalog_df['image_embedding'].values)
#                 logger.info(f"Product catalog created with {len(self.product_catalog_df)} items.")
#             else:
#                 logger.warning("Product catalog is empty after processing.")
#         except Exception as e:
#             logger.error(f"Failed to load or process catalog from file '{catalog_path}': {e}")

#     def find_similar_items(self, cropped_image: Image.Image, class_name: str, top_n: int = 1):
#         """Finds the most similar items in the catalog for a given cropped image."""
#         if self.product_catalog_df is None or self.product_catalog_df.empty:
#             return []

#         input_tensor = self.preprocess(cropped_image)
#         input_batch = input_tensor.unsqueeze(0).to(self.device)
#         with torch.no_grad():
#             query_embedding = self.feature_extractor(input_batch).squeeze().cpu().numpy()

#         # **THIS IS THE FIX from your Colab logic**
#         # It makes the filtering robust to case and whitespace differences.
#         relevant_catalog_df = self.product_catalog_df[
#             self.product_catalog_df['category'].str.strip().str.lower() == class_name.strip().lower()
#         ]
        
#         if relevant_catalog_df.empty:
#             logger.warning(f"No items found in catalog for category: '{class_name}'")
#             return []

#         relevant_embeddings = np.vstack(relevant_catalog_df['image_embedding'].values)
#         similarities = cosine_similarity(query_embedding.reshape(1, -1), relevant_embeddings)[0]
        
#         # This part is also from your Colab: find the top N recommendations
#         num_recommendations = 1
#         top_indices = np.argsort(similarities)[::-1][:num_recommendations]
        
#         results = []
#         for idx in top_indices:
#             product_info = relevant_catalog_df.iloc[idx]
#             results.append({
#                 "product_name": product_info['product_name'],
#                 "product_url": product_info['product_url'],
#                 "similarity_score": float(similarities[idx]),
#                 "image_url": product_info['image_url']
#             })
        
#         return results

# # Instantiate the service
# similarity_service = SimilarityService()

