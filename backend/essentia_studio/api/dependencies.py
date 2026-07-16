from fastapi import Request

from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.services.capabilities import CapabilityService


def get_settings_repository(request: Request) -> SettingsRepository:
    return request.app.state.settings_repository


def get_capability_service(request: Request) -> CapabilityService:
    return request.app.state.capability_service
