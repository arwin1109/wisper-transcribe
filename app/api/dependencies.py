from functools import lru_cache

from app.core.config import get_settings
from app.services.storage import SessionStorage
from app.services.transcriber import FasterWhisperTranscriber


@lru_cache
def get_storage() -> SessionStorage:
    settings = get_settings()
    return SessionStorage(settings.data_dir)


@lru_cache
def get_transcriber() -> FasterWhisperTranscriber:
    settings = get_settings()
    return FasterWhisperTranscriber(
        model_name=settings.model_name,
        device=settings.device,
        compute_type=settings.compute_type,
        cpu_threads=settings.cpu_threads,
        num_workers=settings.num_workers,
    )
