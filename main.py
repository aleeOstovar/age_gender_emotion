from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from routes.websocket_routes import router as ws_router
from routes.api_routes import router as api_router  # Add this import
from pathlib import Path
from config.config import STATIC_DIR
from pyngrok import ngrok

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include both WebSocket and API routes
app.include_router(ws_router)
app.include_router(api_router, prefix="/api")  # Add prefix to avoid conflicts

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Root route
@app.get("/")
async def read_root():
    return FileResponse(str(STATIC_DIR / "index.html"))

if __name__ == "__main__":
    # Set your ngrok auth token here
    AUTH_TOKEN = "2sWdTEp4SLH4zcdMRAvrxaoERyg_4NFX4YfoxJvtyB2sg5ku1"
    ngrok.set_auth_token(AUTH_TOKEN)
    
    host_address="127.0.0.1"

    # Specify the port your app will run on
    port = 8000

    # Open an ngrok tunnel on the specified port
    public_url = ngrok.connect(port, proto="http")
    print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}/\"")

    # Now start the Uvicorn server
    import uvicorn
    uvicorn.run("main:app", host=host_address, port=port, reload=True)