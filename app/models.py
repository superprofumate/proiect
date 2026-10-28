from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Client(StrictModel):
    client_id: int = Field(gt=0)
    nivel_relatie: int = Field(ge=1, le=3)
    scor_risc: float = Field(ge=0, le=1)
    flag_frauda_interna: bool
    flag_pep: bool

class Rules(StrictModel):
    version: str = Field(min_length=1)
    high_risk_threshold: float = Field(ge=0, le=1)
    low_relationship_max: int = Field(ge=1, le=3)

class Decision(StrictModel):
    client_id: int
    rules_version: str
    action: Literal['manual_review', 'relationship_check_in', 'standard_follow_up']
    reasons: list[str]
    requires_human_review: bool = True

class Request(StrictModel):
    client_id: int = Field(gt=0)
    explain: bool = False

class Response(StrictModel):
    request_id: str
    decision: Decision
    explanation: str | None = None
