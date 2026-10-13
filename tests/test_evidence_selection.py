import json
import unittest
from pathlib import Path
from services.ingest import load_dataset
from services.answering import answer

ROOT=Path(__file__).resolve().parents[1]


class EvidenceSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=load_dataset(ROOT)

    def test_model_can_choose_real_lines_across_topics_without_writing_an_answer(self):
        from services.evidence_selection import select_evidence
        for topic in ['bubble','selection','insertion','merge','counting']:
            row=next(c for c in self.data['chunks'] if c['topic']==topic and c['kind']=='paragraph')
            def generate(prompt):
                payload=json.loads(prompt)
                self.assertEqual(payload['question'],'คำถามทั่วไป')
                return {'intent':'explanation','selections':[dict(id=row['id'],first_line=row['line_ids'][0],last_line=row['line_ids'][-1])]}
            result=select_evidence('คำถามทั่วไป',[row],self.data,generate=generate)
            self.assertEqual(result['state'],'selected')
            self.assertEqual(result['evidence'][0]['text'],row['text'])

    def test_numeric_page_line_numbers_resolve_only_inside_selected_chunk(self):
        from services.evidence_selection import select_evidence
        row=next(c for c in self.data['chunks'] if c['page']==46 and 'Selection sort divides' in c['text'])
        source_ids=row['line_ids'][1:] if row['contains_heading'] else row['line_ids']
        first=int(source_ids[0].split('-l')[-1]);last=int(source_ids[-1].split('-l')[-1])
        result=select_evidence('selection',[row],self.data,generate=lambda _:{'intent':'definition','selections':[dict(id=row['id'],first_line=first,last_line=last)]})
        self.assertEqual(result['state'],'selected')
        self.assertEqual(result['evidence'][0]['line_ids'],source_ids)
        self.assertIn('Selection sort divides',result['evidence'][0]['text'])
        result=select_evidence('selection',[row],self.data,generate=lambda _:{'intent':'definition','selections':[dict(id=row['id'],first_line=999999,last_line=last)]})
        self.assertEqual(result['state'],'unavailable')

    def test_partial_prose_selection_keeps_the_complete_paragraph(self):
        from services.evidence_selection import select_evidence
        row=next(c for c in self.data['chunks'] if c['page']==36 and c['title']=='The CLRS direction')
        result=select_evidence('bubble sort',[row],self.data,generate=lambda _:{'intent':'definition','selections':[
            dict(id=row['id'],first_line=row['line_ids'][1],last_line=row['line_ids'][-3])]})
        self.assertEqual(result['state'],'selected')
        self.assertIn('arrays and invariants differ.',result['evidence'][0]['text'])
        self.assertTrue(result['evidence'][0]['text'].endswith('one pass.'))
        self.assertEqual(result['evidence'][0]['line_ids'],row['line_ids'][1:])

    def test_prose_continuations_are_completed_across_pages_without_expanding_the_section(self):
        from collections import defaultdict
        from services.evidence_selection import select_evidence
        groups=defaultdict(list)
        for c in self.data['chunks']:
            if c['kind'] in ('paragraph','list'):groups[c['paragraph_id']].append(c)
        cross=[g for g in groups.values() if len({c['page'] for c in g})>1]
        self.assertTrue(cross)
        for siblings in cross:
            first=siblings[0];line=first['line_ids'][1 if first.get('contains_heading') else 0]
            result=select_evidence('Explain',[first],self.data,generate=lambda _,c=first,l=line:{'intent':'explanation','selections':[
                dict(id=c['id'],first_line=l,last_line=l)]})
            self.assertEqual(result['state'],'selected')
            self.assertEqual([c['id'] for c in result['evidence']],[c['id'] for c in siblings])
            for c in result['evidence']:
                self.assertEqual(c['text'],self.data['pages'][c['page']-1]['text'][c['char_start']:c['char_end']])

    def test_unknown_ids_changed_text_and_reversed_lines_are_rejected(self):
        from services.evidence_selection import select_evidence
        row=next(c for c in self.data['chunks'] if c['text'].startswith('STABLE-SELECTION(A)'))
        correct=dict(id=row['id'],first_line=row['line_ids'][0],last_line=row['line_ids'][-1])
        bad=[dict(correct,id='invented'),dict(correct,text='new answer'),
             dict(correct,first_line=correct['last_line'],last_line=correct['first_line'])]
        for selection in bad:
            result=select_evidence('โค้ด',[row],self.data,generate=lambda p,s=selection:{'intent':'code','selections':[s]})
            self.assertEqual(result['state'],'unavailable')

    def test_valid_empty_selection_refuses_instead_of_using_irrelevant_top_result(self):
        result=answer('Selection Sort มีการส่งอีเมลไหม',self.data,ROOT,
            select_generate=lambda p:{'intent':'out_of_scope','selections':[]})
        self.assertEqual(result['status'],'insufficient_evidence')

    def test_exact_heading_bypasses_model_and_keeps_all_children(self):
        def forbidden(prompt):self.fail('Exact heading lookup must not call the selector')
        for query in ['Efficiency','ประสิทธิภาพ','อ่าน Bubble Sort ทั้งบท']:
            result=answer(query,self.data,ROOT,select_generate=forbidden)
            self.assertEqual(result['selection_state'],'direct_lookup')
            if query!='อ่าน Bubble Sort ทั้งบท':self.assertEqual({e['page'] for e in result['evidence']},{7,8})

    def test_numbered_supplement_heading_is_case_insensitive(self):
        def forbidden(prompt):self.fail('Exact numbered heading must bypass selector')
        for prefix in ['S6.7','s6.7']:
            result=answer(prefix+' Counting sort: deep questions, limits, and corpus audit',self.data,ROOT,select_generate=forbidden)
            self.assertEqual(result['selection_state'],'direct_lookup')
            self.assertEqual({e['page'] for e in result['evidence']},{100})

    def test_literal_question_shaped_headings_still_use_complete_parent_lookup(self):
        def forbidden(_):self.fail('Literal corpus heading must bypass selector')
        for title in ['Front matter','Why sorting?','What stability guarantees','S3.5 Selection sort: why the usual exchange is unstable']:
            node=next(n for n in self.data['nodes'] if n['title']==title)
            result=answer(title,self.data,ROOT,select_generate=forbidden)
            self.assertEqual(result['status'],'answered',title)
            self.assertEqual([c['id'] for c in result['evidence']],node['chunk_ids'],title)

    def test_code_cannot_be_cut_and_candidate_pool_is_bounded(self):
        from services.evidence_selection import select_evidence,candidate_pool
        row=next(c for c in self.data['chunks'] if c['text'].startswith('STABLE-SELECTION(A)'))
        result=select_evidence('โค้ด',[row],self.data,generate=lambda p:{'intent':'code','selections':[
            dict(id=row['id'],first_line=row['line_ids'][0],last_line=row['line_ids'][1])]})
        self.assertEqual(result['state'],'unavailable')
        pool=candidate_pool('sort algorithms',self.data)
        self.assertLessEqual(len(pool),48)
        self.assertLessEqual(sum(len(c['text']) for c in pool),18000)
        self.assertFalse(any('Semantic questions and answers' in c['text'] for c in pool))

    def test_bare_algorithm_and_natural_question_use_generic_model_selector(self):
        for query in ['Bubble Sort','Selection Sort คืออะไร','Insertion Sort ทำงานอย่างไร','Merge Sort แบ่งข้อมูลยังไง','Counting Sort ใช้กับข้อมูลแบบไหน']:
            calls=[]
            def generate(prompt):
                payload=json.loads(prompt);calls.append(payload)
                from services.retrieval import plan_query
                source_by_id={chunk['id']:chunk for chunk in self.data['chunks']}
                requested=set(plan_query(query)['topics'])
                row=next(r for r in payload['candidates'] if r['kind']=='paragraph'
                         and source_by_id[r['id']]['topic'] in requested)
                return {'intent':'explanation','selections':[dict(id=row['id'],first_line=row['lines'][0]['id'],last_line=row['lines'][-1]['id'])]}
            result=answer(query,self.data,ROOT,select_generate=generate)
            self.assertEqual(len(calls),1,query)
            self.assertEqual(result['selection_state'],'selected',query)
            self.assertIn(result['retrieval_method'],['llm_selected','llm_selected_with_definition'],query)


if __name__=='__main__':unittest.main()
