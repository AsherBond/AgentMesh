import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from ..common.models import (
    Task, TaskStatus, WebSocketMessage, TaskSubmitResponse,
    AgentDecisionMessage, AgentThinkingMessage, ToolDecisionMessage,
    ToolExecuteMessage, AgentResultMessage, TaskResultMessage
)
from ..service.task_service import task_service


class WebSocketManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.task_connections: Dict[str, Set[str]] = {}  # task_id -> set of connection_ids
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
    
    def disconnect(self, connection_id: str):
        """Disconnect a WebSocket client"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from task connections
        for task_id, connections in self.task_connections.items():
            if connection_id in connections:
                connections.remove(connection_id)
                if not connections:
                    del self.task_connections[task_id]
    
    def subscribe_to_task(self, connection_id: str, task_id: str):
        """Subscribe a connection to a specific task"""
        if task_id not in self.task_connections:
            self.task_connections[task_id] = set()
        self.task_connections[task_id].add(connection_id)
    
    async def send_message(self, connection_id: str, message: WebSocketMessage):
        """Send message to a specific connection"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(message.json())
            except Exception as e:
                print(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast_to_task(self, task_id: str, message: WebSocketMessage):
        """Broadcast message to all connections subscribed to a task"""
        if task_id in self.task_connections:
            for connection_id in self.task_connections[task_id].copy():
                await self.send_message(connection_id, message)


class TaskProcessor:
    """Task processor for handling task execution"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.running_tasks: Dict[str, asyncio.Task] = {}
    
    async def process_user_input(self, connection_id: str, user_input: dict) -> str:
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
        await self.websocket_manager.send_message(connection_id, submit_response)
        
        return task_id
    
    async def execute_task(self, task_id: str, task_content: str):
        """Execute task and send progress updates"""
        try:
            # Simulate agent decision
            await self._send_agent_decision(task_id, "search_agent", "Search Agent", "Search for relevant information")
            
            # Simulate agent thinking
            await self._send_agent_thinking(task_id, "search_agent", "I need to search for information about this topic...")
            
            # Simulate tool decision
            await self._send_tool_decision(task_id, "search_agent", "google_search", "Google Search", 
                                         "I'll use Google Search to find relevant information", 
                                         {"query": task_content})
            
            # Simulate tool execution
            await self._send_tool_execute(task_id, "search_agent", "google_search", "Google Search", "success", 200,
                                        {
                                            "type": "search_results",
                                            "results": [
                                                {
                                                    "title": "Sample Search Result",
                                                    "url": "https://example.com",
                                                    "snippet": "This is a sample search result..."
                                                }
                                            ],
                                            "total_results": 1
                                        })
            
            # Simulate agent result
            await self._send_agent_result(task_id, "search_agent", f"Based on my search, here's what I found about: {task_content}")
            
            # Update task status to success
            task_service.update_task_status(task_id, TaskStatus.SUCCESS)
            
            # Send task completion
            await self._send_task_result(task_id, "success")
            
        except Exception as e:
            print(f"Error executing task {task_id}: {e}")
            # Update task status to failed
            task_service.update_task_status(task_id, TaskStatus.FAILED)
            await self._send_task_result(task_id, "failed")
    
    async def _send_agent_decision(self, task_id: str, agent_id: str, agent_name: str, sub_task: str):
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
        await self.websocket_manager.broadcast_to_task(task_id, message)
        await asyncio.sleep(0.5)  # Small delay for realistic flow
    
    async def _send_agent_thinking(self, task_id: str, agent_id: str, thought: str):
        """Send agent thinking message"""
        message = AgentThinkingMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "thought": thought
            }
        )
        await self.websocket_manager.broadcast_to_task(task_id, message)
        await asyncio.sleep(0.3)
    
    async def _send_tool_decision(self, task_id: str, agent_id: str, tool_id: str, tool_name: str, thought: str, parameters: dict):
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
        await self.websocket_manager.broadcast_to_task(task_id, message)
        await asyncio.sleep(0.5)
    
    async def _send_tool_execute(self, task_id: str, agent_id: str, tool_id: str, tool_name: str, status: str, execution_time: int, tool_result: dict):
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
        await self.websocket_manager.broadcast_to_task(task_id, message)
        await asyncio.sleep(0.5)
    
    async def _send_agent_result(self, task_id: str, agent_id: str, result: str):
        """Send agent result message"""
        message = AgentResultMessage(
            task_id=task_id,
            data={
                "agent_id": agent_id,
                "result": result
            }
        )
        await self.websocket_manager.broadcast_to_task(task_id, message)
        await asyncio.sleep(0.3)
    
    async def _send_task_result(self, task_id: str, status: str):
        """Send task completion message"""
        message = TaskResultMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "status": status
            }
        )
        await self.websocket_manager.broadcast_to_task(task_id, message)


# Global instances
websocket_manager = WebSocketManager()
task_processor = TaskProcessor(websocket_manager) 