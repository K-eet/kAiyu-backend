# 🏡 kAiyu Backend

**AI Interior Design Web App**

This backend enables users to **upload empty room images**, select **room types** and **style preferences**, and generate **furniture-filled designs** using **IKEA products**.


---

## 📁 Project Structure

This repository contains the backend system built with:

- **FastAPI** for the web API
- **PostgreSQL** for the database
- **SQLAlchemy** for ORM
- **Pydantic** for data validation
- **pgAdmin4** for database management

---

## 🚀 Getting Started
#### Follow these steps to set up the backend locally.

### 📁 1. Clone the Repository

```bash
1. git clone https://github.com/K-eet/kAiyu-backend.git
2. cd kAiyu-backend
```

## Backend Setup 

### 🐍 2. Set Up Virtual Environment

1. **Create the virtual environment**  
   `python -m venv .venv`

2. **Activate the virtual environment**

   - *For Windows (Bash):*  
     `source .venv/Scripts/activate`

   - *For Windows (Command Prompt):*  
     `.venv\Scripts\activate`

> ⚠️ **Important:** Add `.venv` to your `.gitignore` to avoid committing unnecessary files and folders related to your local Python environment.

### 📦 3. Install Dependencies

`pip install -r requirements.txt`

### 🛢️ 4. Set Up PostgreSQL Database

1. Open pgAdmin4 or your preferred PostgreSQL client.
2. Create a new database named: furniture_db
  
### 🔐 5. Configure Environment Variables

1. In the **`backend/`** directory, create a `.env` file.
2. Add the following variables:

```env
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_NAME=furniture_db
```

⚠️ Important: Add .env to your .gitignore to keep your credentials safe.

### 🚦 6. Run the FastAPI Server

1. Make sure you're in the root directory (/kAiyu-backend) and run:
2. `uvicorn backend.main:app --reload` 
3. The server will start at: http://127.0.0.1:8000
4. http://127.0.0.1:8000/docs to open the Swagger UI

### 🛋️ 7. Import Furniture Data

You can import furniture data using one of the following methods:

#### ✅ Method 1: Using Python Script

1. In a **new terminal window**, run:
`python -m backend.scripts.import_furniture`
2. Another method is to **Import/Export Data** from the pgAdmin4 itself. Use the data under the database folder called **furniture_table.csv**

#### ✅ Method 2: Using pgAdmin4 (Manual Import)
1. Open pgAdmin4 and connect to your **furniture_db** database.
2. Navigate to the appropriate table (e.g., furniture).
3. Use the Import/Export feature to import data manually.
4. Select the CSV file located at:
**/database/furniture_table.csv**