"""Offline, source-grounded coverage across fundamental student question families.

This suite tests deterministic basic routing. It deliberately simulates no API
rather than asserting that Gemini answers every broad or qualified question.
"""
import itertools
import unittest
from pathlib import Path

from services.answering import answer_question
from services.common_questions import source_ids_for
from services.ingest import load_dataset
from services.translation import LOCAL_SOURCE_TRANSLATIONS,translate_passages

ROOT=Path(__file__).resolve().parents[1]
TOPICS=('Bubble','Selection','Insertion','Merge','Counting')


class CoreStudentQuestionAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_dataset(ROOT)

    def source_checked(self,question):
        result=answer_question(question,self.data,ROOT,[],generate=None)
        self.assertEqual(result['status'],'answered',question)
        self.assertFalse(result['choices'],question)
        self.assertTrue(result['evidence'],question)
        self.assertLessEqual(len(result['evidence']),11,question)
        for item in result['evidence']:
            page=self.data['pages'][item['page']-1]
            self.assertEqual(item['text'],page['text'][item['char_start']:item['char_end']])
        return result

    def test_definition_mechanism_complexity_stability_and_trace_for_all_five(self):
        for topic in TOPICS:
            queries=[
                f'What is {topic} Sort?',
                f'{topic} Sort คืออะไร',
                f'How does {topic} Sort work?',
                f'{topic} Sort ทำงานอย่างไร',
                f'{topic} Sort time complexity',
                f'{topic} Sort ความซับซ้อน',
                f'Is {topic} Sort stable?',
                f'{topic} Sort เสถียรไหม',
                f'{topic} Sort ทีละขั้น',
            ]
            for q in queries:
                with self.subTest(q=q):
                    result=self.source_checked(q)
                    if 'time complexity' in q or 'ความซับซ้อน' in q:
                        self.assertTrue(any('time' in e['text'].lower() or 'theta' in e['text'].lower() or 'n(' in e['text'].lower() for e in result['evidence']))
                    if 'ทีละขั้น' in q:
                        self.assertGreaterEqual(len(result['evidence']),3)

    def test_all_ten_pairwise_simple_comparisons_have_both_sources(self):
        for a,b in itertools.combinations(TOPICS,2):
            for query in (f'Compare {a} Sort and {b} Sort',f'เปรียบเทียบ {a.lower()} sort กับ {b.lower()} sort'):
                with self.subTest(query=query):
                    result=self.source_checked(query)
                    self.assertEqual(len(result['evidence']),4,query)
                    self.assertEqual(set(e['topic'] for e in result['evidence']),{a.lower(),b.lower()})

    def test_core_course_concepts_have_direct_pdf_evidence(self):
        queries=[
            'What is an algorithm?', 'อัลกอริทึมคืออะไร',
            'What is sorting?', 'การเรียงลำดับคืออะไร',
            'What is Sorting algorithms','1.1 Algorithms',
            'Why is sorting important?','ทำไมต้องเรียงลำดับ',
            'What is time complexity?','What is Big O?',
            'What is stability in sorting?', 'What is auxiliary space?',
            'ประสิทธิภาพ',
            'What is divide and conquer?',
            'What is algorithm correctness?',
            'What is Big Theta?',
            'What is Big Omega?',
            'What is an inversion?',
        ]
        for question in queries:
            with self.subTest(question=question):
                self.source_checked(question)

    def test_notation_bounds_are_not_input_cases_without_gemini(self):
        question='Do Big-O, Omega, and Theta notation identify best, worst, or average cases by themselves?'
        result=self.source_checked(question)
        self.assertEqual(result['retrieval_method'],'common_source_question')
        self.assertIn('do not themselves mean worst, best, or average case',result['answer'])
        self.assertEqual({row['page'] for row in result['evidence']},{29})
        # A 503 must never be reached for this exact locally answerable question.
        same=answer_question(question,self.data,ROOT,[],
            generate=lambda _:self.fail('Simple notation question called Gemini'))
        self.assertEqual(same['retrieval_method'],'common_source_question')
        self.assertIsNone(source_ids_for(question+' for a given Bubble Sort input [3,1]'))

    def test_qualified_requests_do_not_get_wrong_prepared_answer(self):
        for question in (
            'Why does Merge Sort need auxiliary space?',
            'Bubble Sort [9,5,2] step by step',
            'Compare Bubble Sort and Merge Sort for stable descending data',
            'Is Selection Sort stable if equal keys are swapped?',
        ):
            with self.subTest(question=question):
                self.assertIsNone(source_ids_for(question),question)

    def test_streamlit_pair_comparison_is_grouped_by_algorithm(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        app.chat_input[0].set_value('เปรียบเทียบ bubble sort กับ merge sort').run()
        self.assertFalse(app.exception)
        self.assertEqual({r['topic'] for r in app.session_state['messages'][-1]['evidence']},{'bubble','merge'})
        markdown=[m.value for m in app.markdown]
        self.assertTrue(any('#### Bubble Sort' in m for m in markdown))
        self.assertTrue(any('#### Merge Sort' in m for m in markdown))

    def test_selection_stability_cites_actual_unstable_counterexample(self):
        result=self.source_checked('Is Selection Sort stable?')
        self.assertEqual({e['page'] for e in result['evidence']},{50})
        self.assertIn('reversing',result['answer'])
        self.assertIn('original order',result['answer'])

    def test_simple_comparison_does_not_include_unrelated_algorithms(self):
        result=self.source_checked('เปรียบเทียบ bubble sort กับ merge sort')
        self.assertEqual({e['topic'] for e in result['evidence']},{'bubble','merge'})
        self.assertEqual({e['page'] for e in result['evidence']},{34,40,72,78})


class TranslationDiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_dataset(ROOT)

    def test_curated_common_english_sources_have_thai_offline(self):
        indexed={c['id']:c for c in self.data['chunks']}
        rows=[indexed[cid] for cid in LOCAL_SOURCE_TRANSLATIONS]
        output=translate_passages(rows,generate=None)
        self.assertEqual(set(output),set(LOCAL_SOURCE_TRANSLATIONS))
        for cid in LOCAL_SOURCE_TRANSLATIONS:
            with self.subTest(cid=cid):
                self.assertTrue(output[cid]['translated'])
                self.assertEqual(output[cid]['reason'],'local_source_locked')
                self.assertTrue(any('\u0e01' <= ch <= '\u0e7f' for ch in output[cid]['text']))

    def test_reviewed_translation_never_reused_on_mutated_source(self):
        original=next(c for c in self.data['chunks'] if c['id']=='p34-c0344')
        changed=dict(original,text=original['text']+' EXTRA CLAIM')
        output=translate_passages([changed],generate=None)
        self.assertFalse(output[changed['id']]['translated'])
        self.assertEqual(output[changed['id']]['reason'],'translation_requires_provider')

    def test_rejected_marker_and_no_provider_are_distinguishable(self):
        src=dict(id='outside-review',kind='paragraph',text='For 12 values use O(n) time.',protected_spans=['O(n)'])
        error=translate_passages([src],generate=lambda _: {'translations':[{'id':src['id'],'text':'ใช้เวลาน้อย'}]})[src['id']]
        self.assertFalse(error['translated'])
        self.assertEqual(error['reason'],'protected_tokens_mismatch')
        no_api=translate_passages([src],generate=None)[src['id']]
        self.assertEqual(no_api['reason'],'translation_requires_provider')

    def test_retry_failed_translation_does_not_remove_successful_chunks(self):
        from unittest.mock import patch
        import app
        messages=[dict(display_text={
            'failed':dict(text='English',translated=False,reason='translation_unavailable'),
            'done':dict(text='คำแปลที่ผ่านแล้ว',translated=True,reason='local_source_locked'),
        })]
        with patch.object(app.st,'session_state',{'messages':messages}):
            app.retry_failed_translations(0,['failed','done'])
        self.assertNotIn('failed',messages[0]['display_text'])
        self.assertTrue(messages[0]['display_text']['done']['translated'])

    def test_streamlit_offers_retry_after_provider_failure(self):
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest
        calls=[]
        def translator(rows,**kwargs):
            calls.append(len(rows))
            if len(calls)==1:
                return {r['id']:dict(text=r['text'],translated=False,reason='translation_unavailable') for r in rows}
            return {r['id']:dict(text='ข้อมูลเรียงลำดับจากต้นฉบับ',translated=True,reason='protected_tokens_verified') for r in rows}
        with patch.dict('os.environ',{'GEMINI_API_KEY':'test-key'}), \
             patch('services.translation.translate_passages',side_effect=translator):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
            app.toggle[0].set_value(True).run()
            app.chat_input[0].set_value('What is sorting?').run()
            self.assertFalse(app.exception)
            retry=next(b for b in app.button if b.label=='ลองแปลข้อความที่ยังไม่สำเร็จอีกครั้ง')
            retry.click().run()
        self.assertFalse(app.exception)
        self.assertGreaterEqual(len(calls),2)
        self.assertTrue(any('ข้อมูลเรียงลำดับจากต้นฉบับ' in m.value for m in app.markdown))

    def test_default_thai_reading_of_bare_algorithms_has_no_literal_escaped_newlines(self):
        from streamlit.testing.v1 import AppTest
        for question,expected_pages in (
            ('bubble sort',{34}),
            ('merge sort',{72}),
            ('counting sort',{90}),
            ('What is Bubble Sort?',{34}),
        ):
            with self.subTest(question=question):
                app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
                self.assertTrue(app.toggle[0].value)
                app.chat_input[0].set_value(question).run()
                self.assertFalse(app.exception)
                msg=app.session_state['messages'][-1]
                self.assertEqual(msg['status'],'answered')
                self.assertTrue(msg['translate_enabled'])
                self.assertEqual({x['page'] for x in msg['evidence']},expected_pages)
                for item in msg['evidence']:
                    shown=msg['display_text'][item['id']]
                    self.assertTrue(shown['translated'],question+' '+item['id'])
                    self.assertNotIn(r'\n',shown['text'])
                self.assertTrue(any('Bubble Sort' in m.value or 'Merge Sort' in m.value or 'Counting Sort' in m.value
                                    for m in app.markdown))

    def test_simple_bubble_definition_does_not_show_trace_internals(self):
        result=answer_question('What is Bubble Sort?',self.data,ROOT,[],generate=None)
        self.assertEqual(result['status'],'answered')
        self.assertEqual([row['id'] for row in result['evidence']],['p34-c0344'])
        self.assertNotIn('CLRS direction',result['answer'])
        mechanism=answer_question('Bubble Sort ทำงานอย่างไร',self.data,ROOT,[],generate=None)
        self.assertEqual({row['id'] for row in mechanism['evidence']},{'p34-c0344','p36-c0370'})

    def test_simple_merge_definition_contains_divide_conquer_combine(self):
        result=answer_question('merge sort',self.data,ROOT,[],generate=None)
        self.assertEqual(result['status'],'answered')
        self.assertEqual({row['id'] for row in result['evidence']},
                         {'p72-c0759','p72-c0760','p72-c0761','p72-c0762'})
        self.assertIn('Divide:',result['answer'])
        self.assertIn('Conquer:',result['answer'])
        self.assertIn('Combine:',result['answer'])

    def test_source_locked_translation_rejects_changed_formula_numbers(self):
        from unittest.mock import patch
        chunk=next(x for x in self.data['chunks'] if x['id']=='p40-c0415')
        sha,thai=LOCAL_SOURCE_TRANSLATIONS[chunk['id']]
        with patch.dict(LOCAL_SOURCE_TRANSLATIONS,{chunk['id']:(sha,thai+' 999') } ):
            output=translate_passages([chunk],generate=None)[chunk['id']]
        self.assertFalse(output['translated'])
        self.assertEqual(output['reason'],'translation_requires_provider')

    def test_pairwise_bubble_merge_keeps_formulas_in_thai_without_model(self):
        result=answer_question('เปรียบเทียบ Bubble Sort กับ Merge Sort',self.data,ROOT,[],generate=None)
        self.assertEqual(result['status'],'answered')
        translations=translate_passages(result['evidence'],generate=None)
        self.assertTrue(all(t['translated'] for t in translations.values()))
        bubble=translations['p40-c0415']['text']
        merge=translations['p78-c0826']['text']
        self.assertIn('Theta(n^2)',bubble)
        self.assertIn('n(n-1)/2',bubble)
        self.assertIn('Θ(n lg n)',merge)
        self.assertIn('Θ(n²)',merge)
        self.assertNotIn(r'\n',bubble)
        self.assertNotIn(r'\n',merge)

    def test_fallback_only_api_key_is_accepted_without_primary(self):
        import os
        from unittest.mock import patch
        import app
        with patch.object(app,'dotenv_values',return_value={}), \
             patch.object(app.st,'secrets',{}), \
             patch.dict(os.environ,{'GEMINI_API_KEY':'','GEMINI_API_KEY_FALLBACK':'test-backup-key'}):
            key,fallback,model=app.configuration()
        self.assertEqual(key,'test-backup-key')
        self.assertIsNone(fallback)
        self.assertEqual(model,'gemini-3.1-flash-lite')

    def test_provider_503_is_not_wrongly_reported_as_missing_dataset(self):
        source=dict(id='plain',kind='paragraph',text='Sorting compares neighboring items.')
        def unavailable(_):raise ValueError('Model unavailable (status 503)')
        output=translate_passages([source],generate=unavailable)['plain']
        self.assertFalse(output['translated'])
        self.assertEqual(output['reason'],'translation_unavailable')
        self.assertEqual(output['text'],source['text'])


if __name__=='__main__':
    unittest.main()
