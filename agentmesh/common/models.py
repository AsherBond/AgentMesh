from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration"""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


class Task(BaseModel):
    """Task entity model"""
    task_id: str = Field(..., description="Task ID")
    task_status: TaskStatus = Field(..., description="Task status")
    task_name: str = Field(..., description="Task name")
    task_content: str = Field(..., description="Task content description")
    submit_time: datetime = Field(..., description="Task submission time")


class TaskQueryRequest(BaseModel):
    """Task query request model"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")
    status: Optional[TaskStatus] = Field(default=None, description="Task status filter")
    task_name: Optional[str] = Field(default=None, description="Task name search")


class TaskQueryResponse(BaseModel):
    """Task query response model"""
    total: int = Field(..., description="Total number of records")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    tasks: List[Task] = Field(..., description="List of tasks")


class ApiResponse(BaseModel):
    """Standard API response model"""
    code: int = Field(..., description="Response status code")
    message: str = Field(..., description="Response message")
    data: Optional[TaskQueryResponse] = Field(default=None, description="Response data")


# WebSocket Models
class WebSocketMessage(BaseModel):
    """Base WebSocket message model"""
    event: str = Field(..., description="Event type")
    task_id: Optional[str] = Field(default=None, description="Task ID")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp")
    data: dict = Field(default_factory=dict, description="Message data")


class UserInputMessage(WebSocketMessage):
    """User input message from frontend"""
    event: str = Field(default="user_input", description="Event type")
    data: dict = Field(..., description="User input data")


class TaskSubmitResponse(WebSocketMessage):
    """Task submission response"""
    event: str = Field(default="user_task_submit", description="Event type")
    data: dict = Field(..., description="Task submission result")


class AgentDecisionMessage(WebSocketMessage):
    """Agent decision message"""
    event: str = Field(default="agent_decision", description="Event type")
    data: dict = Field(..., description="Agent decision data")


class AgentThinkingMessage(WebSocketMessage):
    """Agent thinking process message"""
    event: str = Field(default="agent_thinking", description="Event type")
    data: dict = Field(..., description="Agent thinking data")


class ToolDecisionMessage(WebSocketMessage):
    """Tool decision message"""
    event: str = Field(default="tool_decision", description="Event type")
    data: dict = Field(..., description="Tool decision data")


class ToolExecuteMessage(WebSocketMessage):
    """Tool execution result message"""
    event: str = Field(default="tool_execute", description="Event type")
    data: dict = Field(..., description="Tool execution data")


class AgentResultMessage(WebSocketMessage):
    """Agent result message"""
    event: str = Field(default="agent_result", description="Event type")
    data: dict = Field(..., description="Agent result data")


class TaskResultMessage(WebSocketMessage):
    """Task completion message"""
    event: str = Field(default="task_result", description="Event type")
    data: dict = Field(..., description="Task result data") 