from typing import Any

from pydantic import BaseModel, ConfigDict

from essentia_studio.domain.jobs import JobEvent, JobItemRecord, JobRecord, JobStatus, JobType


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: JobType
    status: JobStatus
    configuration: dict[str, Any]
    parent_job_id: str | None
    total_items: int
    completed_items: int
    failed_items: int
    cancel_requested: bool

    @classmethod
    def from_record(cls, job: JobRecord) -> "JobResponse":
        return cls.model_validate(job)


class JobEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sequence: int
    job_id: str
    kind: str
    payload: dict[str, Any]

    @classmethod
    def from_record(cls, event: JobEvent) -> "JobEventResponse":
        return cls.model_validate(event)


class JobItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    position: int
    value: str
    status: str
    result: dict[str, Any] | None
    error: str | None

    @classmethod
    def from_record(cls, item: JobItemRecord) -> "JobItemResponse":
        return cls.model_validate(item)
