import uuid
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ..service.websocket_service import websocket_manager, task_processor
from ..common.models import UserInputMessage

# Create router
router = APIRouter(tags=["websocket"])


@router.websocket("/api/v1/task/process")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for task processing
    
    Handles real-time task execution and progress updates
    """
    connection_id = str(uuid.uuid4())
    
    try:
        # Accept the WebSocket connection
        await websocket_manager.connect(websocket, connection_id)
        print(f"WebSocket client connected: {connection_id}")
        
        # Handle messages from client
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle different message types
                if message_data.get("event") == "user_input":
                    await handle_user_input(connection_id, message_data)
                else:
                    print(f"Unknown event type: {message_data.get('event')}")
                    
            except WebSocketDisconnect:
                print(f"WebSocket client disconnected: {connection_id}")
                break
            except json.JSONDecodeError:
                print(f"Invalid JSON received from {connection_id}")
                continue
            except Exception as e:
                print(f"Error processing message from {connection_id}: {e}")
                continue
                
    except Exception as e:
        print(f"WebSocket error for {connection_id}: {e}")
    finally:
        # Clean up connection
        websocket_manager.disconnect(connection_id)
        print(f"WebSocket connection cleaned up: {connection_id}")


async def handle_user_input(connection_id: str, message_data: dict):
    """Handle user input message and start task execution"""
    try:
        # Extract user input data
        user_input = message_data.get("data", {})
        text = user_input.get("text", "")
        
        if not text:
            print("Empty user input received")
            return
        
        print(f"Processing user input: {text[:50]}...")
        
        # Process user input and create task
        task_id = await task_processor.process_user_input(connection_id, user_input)
        
        # Start task execution in background
        import asyncio
        asyncio.create_task(task_processor.execute_task(task_id, text))
        
        print(f"Task {task_id} started for connection {connection_id}")
        
    except Exception as e:
        print(f"Error handling user input: {e}")
        # Send error response to client
        error_message = {
            "event": "user_task_submit",
            "data": {
                "status": "failed",
                "msg": f"Failed to process task: {str(e)}"
            }
        }
        await websocket_manager.send_message(connection_id, error_message) 