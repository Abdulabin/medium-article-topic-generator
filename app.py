"""FastAPI web application for Medium Topic Generator."""

import asyncio
import uuid
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from medium_topic_agent.agent import MediumTopicAgent
from medium_topic_agent.utils import setup_logging

# Setup logging
setup_logging()

# Store active connections and tasks
active_connections: dict[str, WebSocket] = {}
task_results: dict[str, dict] = {}


class TopicRequest(BaseModel):
    """Request model for topic generation."""
    background: str = Field(..., min_length=10, description="Professional background")
    keywords: list[str] = Field(..., min_length=1, max_length=10, description="Keywords of interest")
    target_audience: str = Field(default="general tech audience", description="Target audience")


class TopicResponse(BaseModel):
    """Response model for topic generation."""
    task_id: str
    status: str
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application."""
    # Startup
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    yield
    # Shutdown
    active_connections.clear()
    task_results.clear()


app = FastAPI(
    title="Medium Topic Generator",
    description="AI-powered topic suggestions for Medium articles",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def serve_index():
    """Serve the main HTML page."""
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.post("/api/generate", response_model=TopicResponse)
async def generate_topics(request: TopicRequest):
    """Start topic generation process."""
    task_id = str(uuid.uuid4())
    
    # Store initial state
    task_results[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Starting topic generation...",
        "result": None
    }
    
    # Run generation in background
    asyncio.create_task(run_generation(task_id, request))
    
    return TopicResponse(
        task_id=task_id,
        status="pending",
        message="Topic generation started"
    )


async def run_generation(task_id: str, request: TopicRequest):
    """Run the agent in background and update progress."""
    try:
        # Update progress stages
        stages = [
            (10, "Validating input..."),
            (20, "Searching web for trends..."),
            (40, "Fetching research papers..."),
            (60, "Analyzing trends..."),
            (80, "Generating topics..."),
            (90, "Scoring and ranking..."),
        ]
        
        ws = active_connections.get(task_id)
        
        # Send initial progress
        for progress, message in stages[:2]:
            task_results[task_id].update({
                "progress": progress,
                "message": message
            })
            if ws:
                try:
                    await ws.send_json({
                        "type": "progress",
                        "progress": progress,
                        "message": message
                    })
                except:
                    pass
            await asyncio.sleep(0.5)
        
        # Run the actual agent
        agent = MediumTopicAgent()
        
        # Simulate progress during agent run
        async def update_progress():
            for progress, message in stages[2:]:
                await asyncio.sleep(2)
                task_results[task_id].update({
                    "progress": progress,
                    "message": message
                })
                if ws:
                    try:
                        await ws.send_json({
                            "type": "progress",
                            "progress": progress,
                            "message": message
                        })
                    except:
                        pass
        
        progress_task = asyncio.create_task(update_progress())
        
        # Run agent in executor to not block
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: agent.run(
                background=request.background,
                keywords=request.keywords,
                target_audience=request.target_audience,
                skip_clarification=True
            )
        )
        
        progress_task.cancel()
        
        # Update final result
        task_results[task_id].update({
            "status": "success" if result.get("status") == "success" else "error",
            "progress": 100,
            "message": "Topics generated successfully!" if result.get("status") == "success" else result.get("error", "Unknown error"),
            "result": result
        })
        
        if ws:
            try:
                await ws.send_json({
                    "type": "complete",
                    "status": task_results[task_id]["status"],
                    "result": result
                })
            except:
                pass
                
    except Exception as e:
        task_results[task_id].update({
            "status": "error",
            "progress": 0,
            "message": str(e),
            "result": None
        })
        
        ws = active_connections.get(task_id)
        if ws:
            try:
                await ws.send_json({
                    "type": "error",
                    "message": str(e)
                })
            except:
                pass


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """Get the status of a topic generation task."""
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_results[task_id]


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time progress updates."""
    await websocket.accept()
    active_connections[task_id] = websocket
    
    try:
        # Send current state if task exists
        if task_id in task_results:
            await websocket.send_json({
                "type": "status",
                **task_results[task_id]
            })
        
        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        active_connections.pop(task_id, None)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
