"""Regression tests for source heading lookup in actual chatbot queries."""
import unittest
from pathlib import Path

from services.answering import answer_question
from services.evidence_selection import select_evidence
from services.ingest import load_dataset
from services.retrieval import retrieve, plan_query
from services.search import matched_headings

ROOT = Path(__file__).resolve().parents[1]


class ChatbotPendingFixesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(ROOT)

    def test_broad_numbered_heading_returns_its_actual_opening_without_menu(self):
        response = answer_question('1.1 Algorithms', self.data, ROOT, [],
                                   generate=lambda _: self.fail('Exact section needs no Gemini'))
        self.assertEqual(response['status'], 'answered')
        self.assertEqual([c['page'] for c in response['evidence']], [5]*5)
        self.assertEqual(response['choices'], [])
        self.assertIn('Informally, an algorithm', response['answer'])
        self.assertIn('⟨26, 31, 41, 41, 58, 59⟩', response['answer'])

    def test_what_is_sorting_algorithms_uses_intro_even_on_gemini_503(self):
        def unavailable(_):
            raise ValueError('Model unavailable (status 503)')
        for question in ('What is Sorting algorithms', 'What are sorting algorithms?',
                         'What is a sorting algorithm?', 'Sorting algorithms คืออะไร',
                         'อัลกอริทึมการเรียงลำดับคืออะไร'):
            with self.subTest(question=question):
                result = answer_question(question,self.data,ROOT,[],generate=unavailable,
                                         select_generate=unavailable)
                self.assertEqual(result['status'],'answered')
                self.assertEqual(result['choices'],[])
                self.assertEqual(len(result['evidence']),5)
                self.assertEqual({c['page'] for c in result['evidence']},{5})
                self.assertTrue(result['answer'].startswith('1.1' + chr(10) + 'Algorithms'))
                self.assertIn('Input: A sequence of n numbers',result['answer'])
                self.assertIn('Output: A permutation',result['answer'])
                self.assertIn('⟨26, 31, 41, 41, 58, 59⟩',result['answer'])
                self.assertIn('needed to compute a solution to the problem.',result['answer'])
                self.assertNotIn('Because many programs use it',result['answer'])
                for c in result['evidence']:
                    page=self.data['pages'][c['page']-1]
                    self.assertEqual(c['text'],page['text'][c['char_start']:c['char_end']])

    def test_streamlit_question_submit_renders_intro_when_gemini_unavailable(self):
        from streamlit.testing.v1 import AppTest
        from unittest.mock import patch
        def offline_failure(_):
            raise ValueError('Model unavailable (status 503)')
        with patch.dict('os.environ',{'GEMINI_API_KEY':'test-key'}), \
             patch('services.conversation.generation_provider',return_value=offline_failure):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
            app.chat_input[0].set_value('What is Sorting algorithms').run()
        self.assertFalse(app.exception)
        result=app.session_state['messages'][-1]
        self.assertEqual(result['status'],'answered')
        self.assertFalse(result['choices'])
        self.assertEqual(len(result['evidence']),5)
        self.assertEqual({row['page'] for row in result['evidence']},{5})

    def test_wrong_title_with_valid_number_does_not_open_unrelated_section(self):
        self.assertEqual(matched_headings('1.1 Absolutely Not Algorithms', self.data), [])
        self.assertEqual(retrieve('1.1 Absolutely Not Algorithms', self.data), [])

    def test_explicit_section_id_still_opens_complete_source_without_menu(self):
        selected = next(n for n in self.data['nodes'] if n['title']=='1.1 Algorithms')
        result = answer_question('1.1 Algorithms', self.data, ROOT, [],
                                 generate=lambda _: self.fail('Direct section needs no API'),
                                 section_id=selected['id'])
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['choices'], [])
        self.assertEqual({row['id'] for row in result['evidence']}, set(selected['chunk_ids']))

    def test_copied_source_fragment_needs_no_llm(self):
        response = answer_question('A version that always executes', self.data, ROOT, [],
                                   generate=lambda _: self.fail('Copied source text needs no Gemini'))
        self.assertEqual(response['status'], 'answered')
        self.assertTrue(response['evidence'])
        self.assertEqual({row['page'] for row in response['evidence']}, {47})

    def test_plain_steps_query_works_without_llm_and_has_full_trace(self):
        for question in ('Bubble Sort ทีละขั้น', 'Bubble Sort step by step'):
            with self.subTest(question=question):
                response = answer_question(question, self.data, ROOT, [],
                                           generate=lambda _: self.fail('Known steps should be retrieved locally'))
                self.assertEqual(response['status'], 'answered')
                self.assertGreaterEqual(len(response['evidence']), 3)
                self.assertEqual({row['page'] for row in response['evidence']}, {38})

    def test_routing_outage_does_not_present_unrelated_lexical_matches(self):
        def unavailable(_):
            raise ValueError('Model unavailable (status 503)')
        response = answer_question('Merge Sort แบ่งข้อมูลยังไง', self.data, ROOT, [],
                                   generate=unavailable)
        self.assertEqual(response['status'], 'search_unavailable')
        self.assertFalse(response['evidence'])

    def test_model_cannot_select_a_different_algorithm_as_source(self):
        unrelated = next(row for row in self.data['chunks']
                         if row['page'] == 3 and row['kind'] == 'paragraph')
        choice = dict(intent='explanation', selections=[dict(
            id=unrelated['id'], first_line=unrelated['line_ids'][0],
            last_line=unrelated['line_ids'][-1])])
        outcome = select_evidence('Merge Sort แบ่งข้อมูลยังไง', [unrelated], self.data,
                                  generate=lambda _: choice)
        self.assertEqual(outcome['state'], 'unavailable')
        self.assertEqual(outcome['evidence'], [])

    def test_thai_non_image_words_are_not_corrupted(self):
        for text in ('ประสิทธิภาพ', 'คุณภาพ', 'สภาพ', 'สรุป', 'รูปแบบ'):
            with self.subTest(text=text):
                self.assertEqual(plan_query(text)['normalized'], text)
        self.assertIn('diagram', plan_query('ขอรูปภาพ Bubble Sort')['normalized'])

    def test_thai_efficiency_question_uses_full_section_without_llm(self):
        response = answer_question('ประสิทธิภาพ', self.data, ROOT, [],
                                   generate=lambda _: self.fail('Known heading needs no Gemini'))
        self.assertEqual(response['status'], 'answered')
        self.assertEqual({row['page'] for row in response['evidence']}, {7, 8})

    def test_performance_and_thai_efficiency_resolve_to_same_source(self):
        expected = {row['id'] for row in retrieve('Efficiency', self.data)}
        self.assertTrue(expected)
        for question in ('Performance', 'ประสิทธิภาพ', 'อธิบายเรื่องประสิทธิภาพ'):
            with self.subTest(question=question):
                self.assertEqual({row['id'] for row in retrieve(question, self.data)}, expected)


if __name__ == '__main__':
    unittest.main()
