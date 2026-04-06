"""Shared fixtures and helpers for CRDT convergence tests."""

from __future__ import annotations

from typing import Any

import pycrdt
import pytest


@pytest.fixture
def doc_pair() -> tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]:
    """Two independent Yjs documents for convergence testing."""
    return pycrdt.Doc(), pycrdt.Doc()


@pytest.fixture
def doc_trio() -> tuple[pycrdt.Doc[Any], pycrdt.Doc[Any], pycrdt.Doc[Any]]:
    """Three independent Yjs documents for 3-way convergence testing."""
    return pycrdt.Doc(), pycrdt.Doc(), pycrdt.Doc()


def sync_docs(*docs: pycrdt.Doc[Any]) -> None:
    """Bidirectional sync: exchange state vectors and apply deltas.

    Runs two rounds to guarantee convergence with 3+ documents.
    In the first round, doc A may sync to B before B has C's updates.
    The second round propagates those transitive updates.
    """
    for _round in range(2):
        for i, d_src in enumerate(docs):
            for j, d_dst in enumerate(docs):
                if i != j:
                    sv = d_dst.get_state()
                    update = d_src.get_update(sv)
                    d_dst.apply_update(update)


def get_text(doc: pycrdt.Doc[Any]) -> str:
    """Extract the text content from a Yjs document."""
    return str(doc.get("content", type=pycrdt.Text))


def apply_insert(doc: pycrdt.Doc[Any], pos: int, text: str) -> None:
    """Insert text at the given position, clamped to document length."""
    t = doc.get("content", type=pycrdt.Text)
    length = len(str(t))
    clamped = min(pos, length)
    t[clamped:clamped] = text


def apply_delete(doc: pycrdt.Doc[Any], pos: int, length: int = 1) -> bool:
    """Delete `length` characters starting at `pos`, safe for out-of-range.

    Returns False if yrs panics (e.g. multi-byte char offset mismatch).
    """
    t = doc.get("content", type=pycrdt.Text)
    text_len = len(str(t))
    if text_len == 0 or pos >= text_len:
        return True
    end = min(pos + length, text_len)
    try:
        del t[pos:end]
    except BaseException:
        # yrs-0.25.0 panics on remove_range with multi-byte chars
        return False
    return True
