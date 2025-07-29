import uuid
import json
import threading
import time
import signal
import sys
from datetime import datetime
from typing import Dict, Set, Optional, Any

from ..common.models import (
    Task, TaskStatus, WebSocketMessage, TaskSubmitResponse,
    AgentDecisionMessage, AgentThinkingMessage, ToolDecisionMessage,
    ToolExecuteMessage, AgentResultMessage, TaskResultMessage
)
from ..service.task_service import task_service
from ..service.agent_executor import AgentExecutor


class ThreadManager:
    """Thread manager for tracking and cleaning up threads"""
    
    def __init__(self):
        self.active_threads: Set[threading.Thread] = set()
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        self.shutdown()
    
    def add_thread(self, thread: threading.Thread):
        """Add a thread to tracking"""
        with self.lock:
            self.active_threads.add(thread)
    
    def remove_thread(self, thread: threading.Thread):
        """Remove a thread from tracking"""
        with self.lock:
            self.active_threads.discard(thread)
    
    def shutdown(self):
        """Gracefully shutdown all threads"""
        print("Shutting down thread manager...")
        self.shutdown_event.set()
        
        # Wait for all threads to complete (with timeout)
        with self.lock:
            threads_to_wait = list(self.active_threads)
        
        for thread in threads_to_wait:
            if thread.is_alive():
                print(f"Waiting for thread {thread.name} to complete...")
                thread.join(timeout=5.0)  # 5 second timeout
                if thread.is_alive():
                    print(f"Thread {thread.name} did not complete within timeout")
        
        print("Thread manager shutdown complete")


# Global thread manager
thread_manager = ThreadManager()


class WebSocketManager:
    """WebSocket connection manager for any WebSocket implementation"""
    
    def __init__(self):
        self.active_connections: Dict[str, Any] = {}
        self.task_connections: Dict[str, Set[str]] = {}  # task_id -> set of connection_ids
        self.connections_lock = threading.Lock()  # For active_connections
        self.task_lock = threading.Lock()  # For task_connections
        self.shutdown_event = threading.Event()
    
    def connect(self, websocket: Any, connection_id: str):
        """Connect a new WebSocket client"""
        with self.connections_lock:
            self.active_connections[connection_id] = websocket
            print(f"Connection {connection_id} added. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, connection_id: str):
        """Disconnect a WebSocket client"""
        # Remove from active connections
        with self.connections_lock:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
        
        # Remove from task connections
        with self.task_lock:
            for task_id, connections in self.task_connections.items():
                if connection_id in connections:
                    connections.remove(connection_id)
                    if not connections:
                        del self.task_connections[task_id]
    
    def subscribe_to_task(self, connection_id: str, task_id: str):
        """Subscribe a connection to a specific task"""
        with self.task_lock:
            if task_id not in self.task_connections:
                self.task_connections[task_id] = set()
            self.task_connections[task_id].add(connection_id)
    
    def send_message(self, connection_id: str, message: WebSocketMessage):
        """Send message to a specific connection"""
        # Get connection safely
        connection = None
        with self.connections_lock:
            if connection_id in self.active_connections:
                connection = self.active_connections[connection_id]
        
        # Send message outside of lock
        if connection:
            try:
                connection.send(message.model_dump_json())
            except Exception as e:
                print(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    def broadcast_to_task(self, task_id: str, message: WebSocketMessage):
        """Broadcast message to all connections subscribed to a task"""
        # Get connections to broadcast to (outside of lock)
        connections_to_broadcast = []
        with self.task_lock:
            if task_id in self.task_connections:
                connections_to_broadcast = list(self.task_connections[task_id])
        
        # Send messages to each connection (outside of lock)
        for connection_id in connections_to_broadcast:
            self.send_message(connection_id, message)
    
    def shutdown(self):
        """Gracefully shutdown all connections"""
        print("Shutting down WebSocket manager...")
        self.shutdown_event.set()
        
        # Close all active connections
        with self.connections_lock:
            connections_to_close = list(self.active_connections.keys())
        
        for connection_id in connections_to_close:
            try:
                self.disconnect(connection_id)
            except Exception as e:
                print(f"Error closing connection {connection_id}: {e}")
        
        print("WebSocket manager shutdown complete")


class TaskProcessor:
    """Task processor for handling task execution with real AgentMesh streaming"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.agent_executor = AgentExecutor(websocket_manager)
    
    def process_user_input(self, connection_id: str, user_input: dict) -> str:
        """Process user input and create task"""
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Create task in database
        task = Task(
            task_id=task_id,
            task_status=TaskStatus.RUNNING,
            task_name=user_input.get("text", "New Task")[:50],  # Truncate if too long
            task_content=user_input.get("text", ""),
            submit_time=datetime.now()
        )
        
        # Save task to database
        success = task_service.create_task(task)
        if not success:
            raise Exception("Failed to create task")
        
        # Subscribe connection to task
        self.websocket_manager.subscribe_to_task(connection_id, task_id)
        
        # Send task submission response
        submit_response = TaskSubmitResponse(
            task_id=task_id,
            data={
                "status": "success",
                "task_id": task_id,
                "msg": "Task submitted successfully"
            }
        )
        self.websocket_manager.send_message(connection_id, submit_response)
        
        return task_id
    
    def execute_task(self, task_id: str, task_content: str, team_name: str = "general_team"):
        """Execute task with real AgentMesh logic and stream results"""
        try:
            # Check if shutdown is requested
            if thread_manager.shutdown_event.is_set():
                print(f"Shutdown requested, skipping task {task_id}")
                return
            
            # Update task status to running
            task_service.update_task_status(task_id, TaskStatus.RUNNING)
            
            # Execute task with real AgentMesh team using run_async for streaming
            self.agent_executor.execute_task_with_team_streaming(task_id, task_content, team_name)
            
            # Update task status to success
            task_service.update_task_status(task_id, TaskStatus.SUCCESS)
            
        except Exception as e:
            print(f"Error executing task {task_id}: {e}")
            # Update task status to failed
            task_service.update_task_status(task_id, TaskStatus.FAILED)
            self._send_task_result(task_id, "failed")
    
    def _send_agent_decision(self, task_id: str, agent_id: str, agent_name: str, sub_task: str):
        """Send agent decision message"""
        message = AgentDecisionMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_avatar": "",
                "sub_task": sub_task
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)
        time.sleep(0.1)  # Small delay for realistic flow
    
    def _send_agent_thinking(self, task_id: str, agent_id: str, thought: str):
        """Send agent thinking message"""
        message = AgentThinkingMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "thought": thought
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)
        time.sleep(0.1)
    
    def _send_tool_decision(self, task_id: str, agent_id: str, tool_id: str, tool_name: str, thought: str, parameters: dict):
        """Send tool decision message"""
        message = ToolDecisionMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "tool_id": tool_id,
                "tool_name": tool_name,
                "thought": thought,
                "parameters": parameters
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)
        time.sleep(0.1)
    
    def _send_tool_execute(self, task_id: str, agent_id: str, tool_id: str, tool_name: str, status: str, execution_time: int, tool_result: dict):
        """Send tool execution message"""
        message = ToolExecuteMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "tool_id": tool_id,
                "tool_name": tool_name,
                "status": status,
                "execution_time": execution_time,
                "tool_result": tool_result
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)
        time.sleep(0.1)
    
    def _send_agent_result(self, task_id: str, agent_id: str, result: str):
        """Send agent result message"""
        message = AgentResultMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "result": result
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)
        time.sleep(0.1)
    
    def _send_task_result(self, task_id: str, status: str):
        """Send task completion message"""
        message = TaskResultMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "status": status
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)


# Global instances
websocket_manager = WebSocketManager()
agent_executor = AgentExecutor(websocket_manager)
task_processor = TaskProcessor(websocket_manager)


def cleanup_on_exit():
    """Cleanup function to be called on exit"""
    print("Cleaning up resources...")
    websocket_manager.shutdown()
    thread_manager.shutdown()


# Register cleanup function
import atexit
atexit.register(cleanup_on_exit) 