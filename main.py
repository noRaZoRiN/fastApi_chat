from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, ws_chat, groups, messages
from database import init_db

app = FastAPI(title="FastAPI WebSocket Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

@app.on_event("startup")
async def startup_event():
    init_db()

app.include_router(auth.router)
app.include_router(ws_chat.router)
app.include_router(groups.router)
app.include_router(messages.router)

@app.get("/")
async def root():
    return {
        "message": "FastAPI WebSocket Chat",
        "version": "1.0.0",
        "features": [
            "WebSocket for real-time messaging",
            "Database storage for chat history",
            "User authentication with JWT",
            "Group chat functionality",
            "Real-time notifications"
        ]
    }
