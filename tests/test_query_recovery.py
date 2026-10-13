import json
import unittest
from pathlib import Path
from services.answering import answer
from services.ingest import load_dataset

ROOT=Path(__file__).resolve().parents[1]


class QueryRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=load_dataset(ROOT)

    def assert_selection_intro(self,result):
        self.assertEqual(result['status'],'answered')
        self.assertLessEqual(len(result['evidence']),3)
        self.assertEqual({e['page'] for e in result['evidence']},{46})
        self.assertIn('Selection sort divides',result['answer'])
        self.assertNotIn('Exercises',result['answer'])
        self.assertNotIn('order of growth',result['answer'])

    def test_spelling_correction_reaches_actual_retrieval_with_ai_off(self):
        for query in ['selecion sort','selection sort','selction sort','selection sort คืออะไร']:
            result=answer(query,self.data,ROOT)
            self.assert_selection_intro(result)
            self.assertEqual(result['query']['original'],query)

    def test_api_failure_cannot_fall_back_to_an_entire_chapter(self):
        def unavailable(prompt):raise ValueError('Model unavailable (status 429)')
        for query in ['selecion sort','selection sort']:
            result=answer(query,self.data,ROOT,select_generate=unavailable)
            self.assert_selection_intro(result)
            self.assertEqual(result['selection_state'],'unavailable')

    def test_unavailable_selector_does_not_dump_unrelated_keyword_results(self):
        result=answer('Merge Sort แบ่งข้อมูลยังไง',self.data,ROOT,
            select_generate=lambda p:(_ for _ in ()).throw(ValueError('Model unavailable (status 429)')))
        self.assertEqual(result['status'],'search_unavailable')
        self.assertEqual(result['evidence'],[])
        self.assertEqual(result['selection_provider_status'],429)
        self.assertNotIn('ไม่พบข้อมูล',result['answer'])

    def test_model_sees_corrected_query_while_original_remains_visible(self):
        calls=[]
        def generate(prompt):
            payload=json.loads(prompt);calls.append(payload)
            row=next(c for c in payload['candidates'] if c['page']==46 and any('Selection sort divides' in l['text'] for l in c['lines']))
            return dict(intent='definition',selections=[dict(id=row['id'],first_line=row['lines'][0]['id'],last_line=row['lines'][-1]['id'])])
        result=answer('selecion sort',self.data,ROOT,select_generate=generate)
        self.assert_selection_intro(result)
        self.assertEqual(calls[0]['question'],'selection sort')
        self.assertEqual(result['query']['original'],'selecion sort')

    def test_normalized_bare_algorithm_never_requests_a_whole_chapter(self):
        for query,topic in [('inserion sort','insertion'),('merg sort','merge'),('couning sort','counting')]:
            result=answer(query,self.data,ROOT)
            self.assertEqual(result['status'],'answered',query)
            self.assertLessEqual(len(result['evidence']),4,query)
            self.assertTrue(all(e['topic']==topic for e in result['evidence']),query)

    def test_definition_candidates_exclude_proofs_but_complexity_queries_keep_them(self):
        from services.evidence_selection import candidate_pool
        basic=candidate_pool('selection sort',self.data)
        self.assertTrue(any(c['page']==46 for c in basic))
        self.assertFalse(any('correctness' in ' '.join(c['heading_path']).lower() for c in basic))
        costs=candidate_pool('selection sort worst case complexity',self.data)
        self.assertTrue(any(c['page']==49 for c in costs))

    def test_short_thai_definition_request_uses_prose_for_every_algorithm(self):
        from services.evidence_selection import candidate_pool
        for topic in ['bubble','selection','insertion','merge','counting']:
            query=topic+' sort คือ'
            result=answer(query,self.data,ROOT)
            self.assertEqual(result['status'],'answered')
            self.assertEqual(result['retrieval_method'],'definition')
            self.assertFalse(all(e['contains_heading'] for e in result['evidence']))
            self.assertTrue(all(not (c.get('contains_heading') and len(c['line_ids'])==1) for c in candidate_pool(query,self.data)))

    def test_definition_selection_includes_source_definition_before_mechanics(self):
        def mechanics(prompt):
            payload=json.loads(prompt)
            row=next(c for c in payload['candidates'] if any('Bubble sort repeatedly examines' in l['text'] for l in c['lines']))
            return dict(intent='definition',selections=[dict(id=row['id'],first_line=row['lines'][0]['id'],last_line=row['lines'][-1]['id'])])
        result=answer('bubble sort คือ',self.data,ROOT,select_generate=mechanics)
        self.assertIn('sorting algorithm',result['evidence'][0]['text'])
        self.assertEqual(result['evidence'][0]['page'],34)

    def test_guidance_routes_reach_the_model_candidate_pool(self):
        from services.evidence_selection import candidate_pool
        nodes={n['id']:n for n in self.data['nodes']}
        for guidance in self.data['query_guidance']:
            ids=set(nodes[guidance['target_section_id']]['chunk_ids'])
            self.assertTrue(ids & {c['id'] for c in candidate_pool(guidance['query'],self.data)},guidance['query'])

    def test_named_subsection_returns_its_complete_source_passage(self):
        result=answer('The CLRS direction',self.data,ROOT,select_generate=lambda _:self.fail('Heading must bypass selector'))
        self.assertEqual(result['retrieval_method'],'exact_heading')
        self.assertIn('moves left through neighboring positions.',result['answer'])
        self.assertIn('smallest remaining key, and the finalized prefix grows by one.',result['answer'])
        self.assertIn('A trace question must specify the scan direction and what counts as\none pass.',result['answer'])
        node=next(n for n in self.data['nodes'] if n['title']=='The CLRS direction')
        self.assertEqual([c['id'] for c in result['evidence']],node['chunk_ids'])

    def test_bare_bubble_definition_keeps_the_complete_direction_paragraph(self):
        result=answer('bubble sort',self.data,ROOT)
        self.assertIn('arrays and invariants differ.',result['answer'])
        self.assertIn('A trace question must specify the scan direction and what counts as\none pass.',result['answer'])
        self.assertIn('one-inversion property.',result['answer'])

    def test_real_english_words_are_not_rewritten_as_algorithm_names(self):
        from services.retrieval import plan_query
        self.assertEqual(plan_query('section about efficiency')['normalized'],'section about efficiency')


if __name__=='__main__':unittest.main()
