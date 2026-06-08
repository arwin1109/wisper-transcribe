import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None
    audio_duration_seconds: float | None
    processing_time_seconds: float


class FasterWhisperTranscriber:
    def __init__(
        self,
        model_name: str,
        device: str,
        compute_type: str,
        cpu_threads: int,
        num_workers: int,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.num_workers = num_workers
        self._model = None
        self._lock = Lock()

    @property
    def model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
                num_workers=self.num_workers,
            )
        return self._model

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        started_at = time.perf_counter()
        with self._lock:
            segments, info = self.model.transcribe(
                str(audio_path),
                vad_filter=True,
                beam_size=1,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        processing_time = time.perf_counter() - started_at

        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", None),
            audio_duration_seconds=getattr(info, "duration", None),
            processing_time_seconds=processing_time,
        )
