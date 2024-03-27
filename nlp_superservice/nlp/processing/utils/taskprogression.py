from enum import Enum
from typing import List, Tuple


class StepState(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    DONE = "done"
    FAILED = "failed"


class StepProgression:
    def __init__(self, required: bool, initial_state: StepState = StepState.PENDING):
        self._state = initial_state
        self.required = required
        self.progress = 0.0

    def toDict(self) -> dict:
        ret = {"required": self.required}
        if self.required:
            ret["status"] = f"{self._state}"
            ret["progress"] = self.progress
        return ret

    @property
    def state(self) -> StepState:
        return self._state

    @state.setter
    def state(self, state: StepState):
        self._state = state
        if state == StepState.PENDING:
            self.progress = 0.0
        elif state == StepState.DONE:
            self.progress = 1.0


class TaskProgression:
    def __init__(self, steps: List[Tuple[str, bool]]):
        self.steps = {name: StepProgression(required) for name, required in steps}

    def toDict(self) -> dict:
        ret = {"steps": {}}
        for name, value in self.steps.items():
            ret["steps"][name] = value.toDict()
        return ret
