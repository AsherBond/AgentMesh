from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..service.task_service import task_service
from ..common.models import TaskQueryRequest, ApiResponse, TaskQueryResponse

# Create router
router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.post("/tasks/query", response_model=ApiResponse)
async def query_tasks(request: TaskQueryRequest) -> ApiResponse:
    """
    Query task list with pagination and filters
    
    Returns:
        ApiResponse: Standard API response with task list data
    """
    try:
        # Call service layer to get tasks
        result = task_service.query_tasks(request)
        
        return ApiResponse(
            code=200,
            message="success",
            data=result
        )
    
    except Exception as e:
        # Log the error (you can add proper logging here)
        print(f"Error querying tasks: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error while querying tasks"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Task API is running"} 