from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router


app = FastAPI()

origins = [
    "http://localhost:5173",  # Default Vite port
    "http://localhost:3000",  # Default create-react-app port
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

# include API routes
app.include_router(router)

# Root endpoint
@app.get("/")
def home():
    return {"message": "Resume Parser API is running!"}
