from typing import Annotated

from fastapi import APIRouter, Depends

from essentia_studio.api.dependencies import get_tag_catalog_service
from essentia_studio.schemas.tag_options import TagOptions
from essentia_studio.services.tag_catalog import TagCatalogService

router = APIRouter(prefix="/tag-options")


@router.get("", response_model=TagOptions)
def tag_options(
    service: Annotated[TagCatalogService, Depends(get_tag_catalog_service)],
) -> TagOptions:
    return service.load()
