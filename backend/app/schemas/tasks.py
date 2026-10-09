"""Request validation with Pydantic. Anything not matching is rejected with HTTP 422."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal["pending", "in_progress", "completed"]
STRICT = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaskCreate(BaseModel):
    model_config = STRICT
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    assigned_to: UUID | None = None


class TaskUpdate(BaseModel):
    model_config = STRICT
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.title is None and self.description is None:
            raise ValueError("Provide at least one of: title, description")
        return self


class StatusUpdate(BaseModel):
    model_config = STRICT
    status: Status


class AssigneeUpdate(BaseModel):
    model_config = STRICT
    assigned_to: UUID | None  # required key; null means "unassign"


class TaskListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["all", "created", "assigned"] = "all"
    status: Status | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
