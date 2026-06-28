from fastapi import HTTPException

from backend.app import public_limits as pl


def test_clamp_max_candidates():
    pl.limits.max_public_max_candidates = 8
    assert pl.clamp_max_candidates(12) == 8
    assert pl.clamp_max_candidates(3) == 3


def test_upload_rate_limit():
    window = pl._SlidingWindow(3600)
    key = "1.2.3.4"
    assert window.count(key) == 0
    window.add(key)
    assert window.count(key) == 1


def test_pdf_bytes_limit():
    pl.limits.max_pdf_bytes = 100
    try:
        pl.check_pdf_bytes(b"x" * 101)
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 413
