import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings, Settings
from database import db
from websocket_manager import ConnectionManager
from services.coldspray_service import get_filtered_data, get_logs_data as get_coldspray_logs
from services import analog_service

# Set up proper logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Remanet Data Ingestion Service")

# Add CORS middleware with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create connection manager instance
manager = ConnectionManager()

# REST endpoint for testing
@app.get("/data/")
async def get_data(
    filter_date: Optional[str] = Query(None),
    settings: Settings = Depends(get_settings)
):
    return await get_filtered_data(filter_date)

# Logs endpoint with data source support
@app.get("/logs/")
async def get_logs_data(
    dataSource: Optional[str] = Query("coldspray", description="Data source: coldspray, analog0, or analog1"),
    filter_date: Optional[str] = Query(None, description="Filter date in format MM/DD/YYYY"),
    settings: Settings = Depends(get_settings)
):
    """
    Get logs data based on the selected data source.
    Supports: coldspray, analog0 (ultrasonic), analog1 (acoustic)
    """
    try:
        if dataSource == "coldspray":
            # Get cold spray data from database ONLY (no sample data)
            result = await get_coldspray_logs(filter_date)
            return {
                "data": result.get("data", []),
                "dataSource": "coldspray",
                "notifications": result.get("notifications", [])
            }
        elif dataSource == "analog0":
            # Get analog sensor 0 (ultrasonic) data from database ONLY
            analog_result = await analog_service.get_logs_data(filter_date, "analog_0")
            return {
                "data": analog_result.get("data", []),
                "dataSource": "analog0",
                "notifications": analog_result.get("notifications", [])
            }
        elif dataSource == "analog1":
            # Get analog sensor 1 (acoustic) data from database ONLY
            analog_result = await analog_service.get_logs_data(filter_date, "analog_1")
            return {
                "data": analog_result.get("data", []),
                "dataSource": "analog1",
                "notifications": analog_result.get("notifications", [])
            }
        else:
            return {
                "error": f"Invalid data source: {dataSource}. Must be 'coldspray', 'analog0', or 'analog1'",
                "data": [],
                "dataSource": dataSource
            }
    except Exception as e:
        logger.error(f"Error in get_logs_data: {e}")
        return {
            "error": str(e),
            "data": [],
            "dataSource": dataSource
        }

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Start broadcast task
    manager.start_broadcast_task()
    
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            logger.info(f"Received message: {data[:100]}")
            
            try:
                message = json.loads(data)
                
                # Update filter if received
                if "filter_date" in message:
                    await manager.update_filter(websocket, message["filter_date"])
                
                # Handle ping messages
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received")
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "connections": len(manager.active_connections),
        "mongodb": "connected" if db.db is not None else "disconnected"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    # Initialize database connection
    db.initialize()
    # Start the broadcast task
    manager.start_broadcast_task()
    logger.info("FastAPI application started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    # Stop the broadcast task
    manager.stop_broadcast_task()
    # Close database connection
    db.close()
    logger.info("FastAPI application shutdown")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
