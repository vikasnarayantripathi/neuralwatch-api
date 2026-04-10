from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth.routes import router as auth_router
from app.cameras.routes import router as cameras_router
from app.relay.routes import router as relay_router
from app.motion.routes import router as motion_router
import uvicorn

app = FastAPI(
    title="NeuralWatch API",
    description="Universal Cloud Camera Recording Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(cameras_router)
app.include_router(relay_router)
app.include_router(motion_router)

@app.get("/")
def root():
    return {"status": "NeuralWatch API is running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
