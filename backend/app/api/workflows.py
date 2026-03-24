from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.orchestration import WorkflowExecutor, WorkflowState, WorkflowType

workflow_executor = WorkflowExecutor()

router = APIRouter()


class WorkflowStartRequest(BaseModel):
    type: WorkflowType
    input_data: Dict[str, Any] = {}


class WorkflowResponse(BaseModel):
    id: UUID
    type: WorkflowType
    state: WorkflowState
    current_step: str
    steps: List[str]
    started_at: datetime
    completed_at: Optional[datetime]
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error: Optional[str]

    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowResponse]
    total: int


@router.post("/start", response_model=WorkflowResponse, status_code=201)
async def start_workflow(request: WorkflowStartRequest):
    workflow_id = workflow_executor.start_workflow(
        workflow_type=request.type,
        input_data=request.input_data
    )
    workflow = workflow_executor.get_workflow(workflow_id)
    
    return WorkflowResponse(
        id=workflow.id,
        type=workflow.type,
        state=workflow.state,
        current_step=workflow.current_step,
        steps=workflow.steps,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        input_data=workflow.input_data,
        output_data=workflow.output_data,
        error=workflow.error
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID):
    workflow = workflow_executor.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return WorkflowResponse(
        id=workflow.id,
        type=workflow.type,
        state=workflow.state,
        current_step=workflow.current_step,
        steps=workflow.steps,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        input_data=workflow.input_data,
        output_data=workflow.output_data,
        error=workflow.error
    )


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    state: Optional[WorkflowState] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    workflows = workflow_executor.list_workflows(
        state=state,
        limit=limit,
        offset=offset
    )
    
    total = len(workflow_executor._workflows)
    
    return WorkflowListResponse(
        workflows=[
            WorkflowResponse(
                id=w.id,
                type=w.type,
                state=w.state,
                current_step=w.current_step,
                steps=w.steps,
                started_at=w.started_at,
                completed_at=w.completed_at,
                input_data=w.input_data,
                output_data=w.output_data,
                error=w.error
            )
            for w in workflows
        ],
        total=total
    )


@router.post("/{workflow_id}/cancel", response_model=WorkflowResponse)
async def cancel_workflow(workflow_id: UUID):
    workflow = workflow_executor.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    success = workflow_executor.cancel_workflow(workflow_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel workflow in current state"
        )
    
    workflow = workflow_executor.get_workflow(workflow_id)
    
    return WorkflowResponse(
        id=workflow.id,
        type=workflow.type,
        state=workflow.state,
        current_step=workflow.current_step,
        steps=workflow.steps,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        input_data=workflow.input_data,
        output_data=workflow.output_data,
        error=workflow.error
    )
