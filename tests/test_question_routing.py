import json
import unittest
from pathlib import Path

from services import answering
from services.ingest import load_dataset

ROOT = Path(__file__).resolve().parents[1]
QUESTION = 'วัตถุประสงค์หลักของการเรียนบลำดับข้อมูล(Sorting) คืออะไร'


class GeminiFirstRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(ROOT)

    def setUp(self):
        self.assertTrue(hasattr(answering, 'answer_question'),
                        'Questions need a Gemini-first routing entry point')

    def node(self, title):
        return next(n for n in self.data['nodes'] if n['title'] == title)

    def check_source(self, result):
        self.assertEqual(result['status'], 'answered')
        for row in result['evidence']:
            page = self.data['pages'][row['page'] - 1]
            self.assertEqual(row['text'], page['text'][row['char_start']:row['char_end']])

    def test_exact_heading_opens_parent_and_children_without_gemini(self):
        node = self.node('The CLRS direction')
        calls = []
        def generate(prompt):
            payload = json.loads(prompt)
            calls.append(payload)
            self.assertNotIn('candidates', payload, 'Direct extraction needs no evidence selector')
            return dict(mode='direct', search_query='The CLRS direction', section_id=node['id'])
        result = answering.answer_question('The CLRS direction', self.data, ROOT, [], generate=generate)
        self.check_source(result)
        self.assertEqual(len(calls), 0)
        self.assertEqual([r['id'] for r in result['evidence']], node['chunk_ids'])
        self.assertIn('A trace question must specify', result['answer'])

    def test_known_thai_topic_alias_opens_source_without_gemini(self):
        result = answering.answer_question(
            'เคาน์ทิงซอท คืออะไร', self.data, ROOT, [],
            generate=lambda _: self.fail('A known Counting Sort alias must not call Gemini'))
        self.check_source(result)
        self.assertEqual(result['retrieval_method'], 'known_topic_alias')
        self.assertIn('Counting sort', result['answer'])

    def test_bare_algorithm_name_uses_concise_definition_instead_of_whole_chapter(self):
        result = answering.answer_question(
            'bubble sort', self.data, ROOT, [],
            generate=lambda _: self.fail('A known Bubble Sort name must not call Gemini'))
        self.check_source(result)
        self.assertEqual(result['retrieval_method'], 'known_topic_alias')
        self.assertLessEqual(len(result['evidence']), 3)
        self.assertIn('Bubble sort', result['answer'])

    def test_common_typo_in_prepared_sorting_question_uses_cached_answer(self):
        result = answering.answer_question(
            QUESTION, self.data, ROOT, [],
            generate=lambda _: self.fail('A prepared question must not call Gemini'))
        self.check_source(result)
        self.assertEqual(result['retrieval_method'], 'prepared_answer')
        self.assertIn('การเรียงลำดับข้อมูล', result['answer'])

    def test_unfamiliar_thai_question_uses_gemini_interpretation_and_real_pdf_evidence_without_vectors(self):
        question = 'เหตุผลเชิงประวัติศาสตร์ที่ทำให้การเรียงลำดับสำคัญคืออะไร'
        node = self.node('Why sorting?')
        calls = []
        def generate(prompt):
            payload = json.loads(prompt)
            calls.append(payload)
            self.assertEqual(payload['question'], question)
            return dict(mode='interpret', search_query='Why sorting?', section_id=node['id'])
        result = answering.answer_question(question, self.data, ROOT, [], generate=generate)
        self.check_source(result)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['query']['original'], question)
        self.assertEqual(result['question_route']['mode'], 'interpret')
        self.assertEqual([row['id'] for row in result['evidence']], node['chunk_ids'])

    def test_invalid_source_target_or_changed_numeric_constraints_cannot_be_used(self):
        for query, route in [
            ('Why study sorting algorithms?', dict(mode='direct', search_query='Why sorting?', section_id='invented')),
            ('bubble sort [9,7,4] right to left',
             dict(mode='interpret', search_query='bubble sort [1,2,3] right to left', section_id=None)),
        ]:
            result = answering.answer_question(query, self.data, ROOT, [], generate=lambda _: route)
            self.assertEqual(result['status'], 'search_unavailable')
            self.assertEqual(result['evidence'], [])

    def test_out_of_scope_route_returns_no_source_answer(self):
        result = answering.answer_question('weather tomorrow', self.data, ROOT, [],
            generate=lambda _: dict(mode='out_of_scope', search_query='weather tomorrow', section_id=None))
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertEqual(result['evidence'], [])

    def test_interpretation_can_change_array_spacing_without_changing_values(self):
        from services.question_routing import interpret_question
        route = interpret_question('bubble sort [9,7,-4] right to left', [], self.data,
            generate=lambda _: dict(mode='interpret', search_query='bubble sort [9, 7, -4] right to left', section_id=None))
        self.assertEqual(route['search_query'], 'bubble sort [9, 7, -4] right to left')

    def test_deployed_submit_flow_routes_before_retrieval(self):
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest
        node = self.node('Why sorting?')
        calls = []
        def generate(prompt):
            payload = json.loads(prompt)
            calls.append(payload)
            return dict(mode='interpret', search_query='Why study sorting algorithms?', section_id=node['id'])
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}), \
             patch('services.conversation.generation_provider', return_value=generate):
            app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=30).run()
            app.chat_input[0].set_value(QUESTION).run()
        self.assertFalse(app.exception)
        result = app.session_state['messages'][-1]
        self.check_source(result)
        self.assertEqual(len(calls), 0)
        self.assertEqual(result['query']['original'], QUESTION)
        self.assertEqual(result['retrieval_method'], 'prepared_answer')


if __name__ == '__main__':
    unittest.main()
