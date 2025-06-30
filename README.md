# kAiyu-backend

# 🏡 AI Interior Design Web App

This is an AI-powered interior design web application that allows users to upload empty room images, select room, and style preferences, and generate furniture-filled designs using IKEA products. 

## 🚀 Getting Started

### 1. Clone the repository

1. git clone https://github.com/K-eet/kAiyu-backend.git
2. cd kAiyu-backend

## Backend Setup 

### 1. Create and activate virtual environment

1. python -m venv .venv  # Create venv
2. source .venv/Scripts/activate  # Activate .venv for windows using Bash command line
3. .venv\Scripts\activate

### 2. Install backend dependencies

1. pip install -r requirements.txt

### 3. Setup PostgreSQL Database

1. Create database called "furniture_db"

### 4. Configure environment variables

1. Create .env file in the backend/ directory
2. Setup the .env as below: 
- DB_USER = ""
- DB_PASSWORD = ""
- DB_HOST = ""
- DB_NAME = ""
3. Fill in the empty string with your own pgAdmin4 credentials
4. Remember to place your .env inside your .gitignore file

### 5. Start FastAPI server

- Open your preferred command line
- uvicorn backend.main:app --reload 
- Make sure your directory is in /kAiyu-backend

### 6. Import furniture data

- Open another command line
- python -m backend.scripts.import_furniture