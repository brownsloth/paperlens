from __future__ import annotations

__all__ = ["SpeechAnnotator", "AnnotatedDocument"]


def __getattr__(name: str):
    if name == "SpeechAnnotator":
        from speechlens.annotator import SpeechAnnotator

        return SpeechAnnotator
    if name == "AnnotatedDocument":
        from speechlens.annotator import AnnotatedDocument

        return AnnotatedDocument
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
