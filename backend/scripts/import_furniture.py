import pandas as pd
from sqlalchemy.orm import Session
from backend.core.database import SessionLocal
from backend.models.models import FurnitureDatabase

def import_csv_to_furniture(csv_path: str):
  df = pd.read_csv(csv_path)
  df.columns = df.columns.str.strip().str.lower()
  session =  SessionLocal()

  for _, row in df.iterrows():
    try: 
      furniture = FurnitureDatabase(
        furniture_id=row["furniture_id"],
        style=row["style"],
        room=row["room"],
        name=row["name"],
        type=row["type"],
        price=row["price"],
        image_link=row["image_link"],
        purchase_link=row["purchase_link"]
      )
      session.add(furniture)
    except Exception as e:
      print(f"Error importing row: {row.to_dict()} => {e}")

  session.commit()
  session.close()
  print("Furniture data imported successfully.")

if __name__ == "__main__":
  import_csv_to_furniture("./database/furniture_table.csv")