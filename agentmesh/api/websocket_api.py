import uuid
import json
import threading
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ..service.websocket_service import websocket_manager, task_processor, thread_manager
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
        await websocket.accept()
        
        # Create a simple connection wrapper for FastAPI WebSocket
        class FastAPIWebSocketWrapper:
            def __init__(self, websocket: WebSocket):
                self.websocket = websocket
                self.connection_id = connection_id
            
            def send(self, message: str):
                """Send message using FastAPI WebSocket"""
                import asyncio
                try:
                    # Create a new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.websocket.send_text(message))
                except Exception as e:
                    print(f"Error sending message: {e}")
                finally:
                    try:
                        loop.close()
                    except:
                        pass
        
        # Create wrapper and register with manager
        ws_wrapper = FastAPIWebSocketWrapper(websocket)
        websocket_manager.connect(ws_wrapper, connection_id)
        print(f"WebSocket client connected: {connection_id}")
        
        # Handle messages from client
        while True:
            try:
                # Check if shutdown is requested
                if thread_manager.shutdown_event.is_set():
                    print(f"Shutdown requested, closing connection {connection_id}")
                    break
                
                # Receive message from client
                data = await websocket.receive_text()
                
                # Process message
                message_data = json.loads(data)
                
                # Handle different message types
                if message_data.get("event") == "user_input":
                    # Start task execution in a separate thread with proper tracking
                    task_thread = threading.Thread(
                        target=handle_user_input,
                        args=(connection_id, message_data),
                        name=f"task-{connection_id}",
                        daemon=False  # Changed to False for better control
                    )
                    
                    # Add thread to manager for tracking
                    thread_manager.add_thread(task_thread)
                    task_thread.start()
                    
                    # Clean up completed threads
                    thread_manager.remove_thread(task_thread)
                    
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


def handle_user_input(connection_id: str, message_data: dict):
    """Handle user input message and start task execution"""
    try:
        # Check if shutdown is requested
        if thread_manager.shutdown_event.is_set():
            print(f"Shutdown requested, skipping task for connection {connection_id}")
            return
        
        # Extract user input data
        user_input = message_data.get("data", {})
        text = user_input.get("text", "")
        team_name = user_input.get("team", "general_team")  # Default to general_team
        
        if not text:
            print("Empty user input received")
            return
        
        print(f"Processing user input: {text[:50]}... with team: {team_name}")
        
        # Process user input and create task
        task_id = task_processor.process_user_input(connection_id, user_input)
        
        # Execute task synchronously (this will stream results via WebSocket)
        task_processor.execute_task(task_id, text, team_name)
        
        print(f"Task {task_id} completed for connection {connection_id} with team {team_name}")
        
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
        websocket_manager.send_message(connection_id, error_message) 