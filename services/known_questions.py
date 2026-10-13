"""Exact benchmark-style recognition.  It never supplies answer text."""
import json
from functools import lru_cache
from pathlib import Path
from .retrieval import compact


@lru_cache(maxsize=1)
def known_questions():
    path=Path(__file__).resolve().parents[1]/'metadata/benchmark_question_styles.json'
    if not path.exists():
        return {}
    return {compact(row['question']):row for row in json.loads(path.read_text())['items']}


def known_negative_question(question):
    row=known_questions().get(compact(question))
    return bool(row and row.get('negative'))
