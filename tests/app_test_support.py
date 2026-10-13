import unittest
import json
import re
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch


@lru_cache(maxsize=1)
def _dataset():
    from services.ingest import load_dataset
    return load_dataset(Path(__file__).resolve().parents[1])


def _offline_generate(prompt):
    """Fake the external Gemini responses, keeping real retrieval and source validation."""
    from services.search import expanded,definition_rows
    from services.retrieval import retrieve
    payload=json.loads(prompt)
    if 'catalog' in payload:
        query=expanded(payload['question'])
        if not re.search('[A-Za-z]',query):query='unknown '+query
        return dict(mode='direct',search_query=query,section_id=payload.get('selected_section_id'))
    if 'candidates' in payload:
        data=_dataset();query=payload['question']
        definitions=definition_rows(query,data)
        rows=definitions or retrieve(query,data)
        supplied={c['id']:c for c in payload['candidates']}
        selected=[supplied[c['id']] for c in rows if c['id'] in supplied][:8]
        return dict(intent='definition' if definitions else 'explanation',selections=[
            dict(id=c['id'],first_line=c['lines'][0]['id'],last_line=c['lines'][-1]['id']) for c in selected])
    raise ValueError('Unexpected offline AI operation')


class OfflineAITestCase(unittest.TestCase):
    """Keep UI tests deterministic without presenting an AI control to users."""

    def setUp(self):
        self._generation_provider_patch = patch(
            'services.conversation.generation_provider', return_value=_offline_generate
        )
        self._generation_provider_patch.start()
        self.addCleanup(self._generation_provider_patch.stop)
