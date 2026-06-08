import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None
    audio_duration_seconds: float | None
    processing_time_seconds: float


class FasterWhisperTranscriber:
    def __init__(self, model_name: str, device: str, compute_type: str) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        started_at = time.perf_counter()
        segments, info = self.model.transcribe(str(audio_path), vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        processing_time = time.perf_counter() - started_at

        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", None),
            audio_duration_seconds=getattr(info, "duration", None),
            processing_time_seconds=processing_time,
        )

