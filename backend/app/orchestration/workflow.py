import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


class WorkflowState(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class WorkflowType(str, Enum):
    pda_only = "pda_only"
    pda_cda = "pda_cda"
    full_pipeline = "full_pipeline"


WORKFLOW_STEPS: Dict[WorkflowType, List[str]] = {
    WorkflowType.pda_only: ["detect_properties", "match_records", "generate_report"],
    WorkflowType.pda_cda: ["detect_properties", "match_records", "detect_changes", "generate_alerts", "generate_report"],
    WorkflowType.full_pipeline: ["detect_properties", "match_records", "detect_changes", "generate_alerts", "update_gua", "generate_report"],
}


@dataclass
class Workflow:
    id: uuid.UUID
    type: WorkflowType
    state: WorkflowState
    current_step: str
    steps: List[str]
    started_at: datetime
    completed_at: Optional[datetime]
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error: Optional[str] = field(default=None)

    def __post_init__(self):
        if not self.steps:
            self.steps = WORKFLOW_STEPS.get(self.type, []).copy()


class WorkflowExecutor:
    def __init__(self):
        self._workflows: Dict[uuid.UUID, Workflow] = {}

    def start_workflow(self, workflow_type: WorkflowType, input_data: Dict[str, Any]) -> uuid.UUID:
        workflow_id = uuid.uuid4()
        steps = WORKFLOW_STEPS.get(workflow_type, []).copy()
        
        workflow = Workflow(
            id=workflow_id,
            type=workflow_type,
            state=WorkflowState.pending,
            current_step=steps[0] if steps else "",
            steps=steps,
            started_at=datetime.utcnow(),
            completed_at=None,
            input_data=input_data,
            output_data={},
        )
        
        self._workflows[workflow_id] = workflow
        self._transition_state(workflow, WorkflowState.running)
        
        return workflow_id

    def get_workflow(self, workflow_id: uuid.UUID) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    def cancel_workflow(self, workflow_id: uuid.UUID) -> bool:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
        
        if workflow.state in (WorkflowState.completed, WorkflowState.failed, WorkflowState.cancelled):
            return False
        
        self._transition_state(workflow, WorkflowState.cancelled)
        return True

    def list_workflows(
        self,
        state: Optional[WorkflowState] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Workflow]:
        workflows = list(self._workflows.values())
        
        if state:
            workflows = [w for w in workflows if w.state == state]
        
        workflows.sort(key=lambda w: w.started_at, reverse=True)
        
        return workflows[offset:offset + limit]

    async def _execute_step(self, workflow: Workflow, step_name: str) -> bool:
        try:
            workflow.output_data[step_name] = {"status": "completed", "timestamp": datetime.utcnow().isoformat()}
            
            current_index = workflow.steps.index(step_name)
            if current_index < len(workflow.steps) - 1:
                workflow.current_step = workflow.steps[current_index + 1]
            else:
                workflow.current_step = step_name
                self._transition_state(workflow, WorkflowState.completed)
                workflow.completed_at = datetime.utcnow()
            
            return True
        except Exception as e:
            workflow.error = str(e)
            self._transition_state(workflow, WorkflowState.failed)
            return False

    def _transition_state(self, workflow: Workflow, new_state: WorkflowState) -> None:
        valid_transitions = {
            WorkflowState.pending: [WorkflowState.running, WorkflowState.cancelled],
            WorkflowState.running: [WorkflowState.paused, WorkflowState.completed, WorkflowState.failed, WorkflowState.cancelled],
            WorkflowState.paused: [WorkflowState.running, WorkflowState.cancelled],
            WorkflowState.completed: [],
            WorkflowState.failed: [],
            WorkflowState.cancelled: [],
        }
        
        if new_state in valid_transitions.get(workflow.state, []):
            workflow.state = new_state
