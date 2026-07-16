from fastapi import Request

from essentia_studio.playlists.storage import PlaylistStorage
from essentia_studio.repositories.jobs import JobRepository
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.repositories.writes import WriteRepository
from essentia_studio.services.capabilities import CapabilityService
from essentia_studio.services.jobs import JobCoordinator
from essentia_studio.services.tag_operations import TagOperationService


def get_settings_repository(request: Request) -> SettingsRepository:
    return request.app.state.settings_repository


def get_capability_service(request: Request) -> CapabilityService:
    return request.app.state.capability_service


def get_job_repository(request: Request) -> JobRepository:
    return request.app.state.job_repository


def get_track_repository(request: Request) -> TrackRepository:
    return request.app.state.track_repository


def get_result_repository(request: Request) -> ResultRepository:
    return request.app.state.result_repository


def get_job_coordinator(request: Request) -> JobCoordinator:
    return request.app.state.job_coordinator


def get_write_repository(request: Request) -> WriteRepository:
    return request.app.state.write_repository


def get_tag_operation_service(request: Request) -> TagOperationService:
    return request.app.state.tag_operation_service


def get_playlist_storage(request: Request) -> PlaylistStorage:
    return request.app.state.playlist_storage
