"""Acceptance regressions: omitted headings, image gating, lost parent pages."""
import copy
import tempfile
import unittest
from pathlib import Path
import pymupdf
from services.ingest import extract_document, load_dataset
from services.retrieval import retrieve
from services.answering import answer

ROOT=Path(__file__).resolve().parents[1]

class EnglishSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=extract_document(ROOT/'book_data/Cormen_Basic_Sorting_100_Pages.pdf',ROOT,language='en')

    def test_efficiency_heading_returns_continuation_on_next_page(self):
        rows=retrieve('Efficiency',self.data)
        self.assertEqual({r['page'] for r in rows},{7,8})
        self.assertIn('more than 17 times',' '.join(r['text'] for r in rows))
        self.assertTrue(all(r['retrieval_method']=='exact_heading' for r in rows))

    def test_thai_heading_uses_same_complete_english_section(self):
        for query in ['ประสิทธิภาพ','อธิบายเรื่องประสิทธิภาพ','Performance']:
            rows=retrieve(query,self.data)
            self.assertTrue(rows,query)
            self.assertEqual({r['id'] for r in rows},{r['id'] for r in retrieve('Efficiency',self.data)})

    def test_original_front_matter_is_searchable(self):
        for query,page in [('ISBN',3),('Contents',4),('Introduction',9)]:
            self.assertIn(page,{r['page'] for r in retrieve(query,self.data)},query)

    def test_plain_english_keyword_is_not_blocked_by_algorithm_allowlist(self):
        self.assertTrue(retrieve('satellite',self.data))

    def test_bubble_definition_is_intro_prose_not_chapter_or_supplement_headings(self):
        for query in ['bubble sort','Bubble Sort','บับเบิลซอส','bubble sort คือ อะไร','Bubble Sort คืออะไร','What is bubble sort?',
                      'ความหมายของบับเบิลซอส','บับเบิลซอร์ตคืออะไร']:
            result=answer(query,self.data,ROOT)
            self.assertEqual(result['status'],'answered',query)
            self.assertEqual(len(result['evidence']),3,query)
            self.assertEqual([e['page'] for e in result['evidence']],[34,36,36])
            self.assertIn('left key is greater than the right key',result['answer'])
            self.assertIn('moves a largest remaining key',result['answer'])
            self.assertNotIn('A right-to-left pass',result['answer'])
            self.assertIn('one inversion',result['answer'])
            self.assertIn('Problem 2-2',result['answer'])
            self.assertIn('arrays and invariants differ.',result['answer'])
            self.assertIn('one pass.',result['answer'])
            row=result['evidence'][0]
            self.assertEqual(row['page'],34)
            self.assertIn('swapping adjacent elements',row['text'])
            self.assertNotIn('Correctness of bubblesort',row['text'])
            self.assertEqual(row['line_ids'],['p34-l16','p34-l17'])
            page=self.data['pages'][33]
            self.assertEqual(row['text'],page['text'][row['char_start']:row['char_end']])
            for evidence in result['evidence']:
                page=self.data['pages'][evidence['page']-1]
                self.assertEqual(evidence['text'],page['text'][evidence['char_start']:evidence['char_end']])

    def test_explicit_whole_chapter_still_expands_parent(self):
        rows=retrieve('อ่าน Bubble Sort ทั้งบท',self.data)
        chapter=next(n for n in self.data['nodes'] if n['kind']=='chapter' and 'bubble' in n['title'].lower())
        self.assertEqual({r['id'] for r in rows},set(chapter['chunk_ids']))
        self.assertGreater(len(rows),4)

    def test_parent_heading_expands_all_descendants_even_over_limit(self):
        rows=retrieve('Principles of sorting',self.data,limit=2)
        self.assertIn(33,{r['page'] for r in rows})
        self.assertGreater(len(rows),2)
        self.assertEqual(rows,sorted(rows,key=lambda r:r['order']))

    def test_hierarchy_and_all_body_lines_are_covered_once(self):
        self.assertEqual(self.data['schema_version'],3)
        nodes={n['id']:n for n in self.data['nodes']}
        seen=[]
        for c in self.data['chunks']:
            self.assertIn(c['paragraph_id'],nodes)
            self.assertIn(c['parent_id'],nodes)
            self.assertTrue(c['heading_path'])
            seen.extend(c['line_ids'])
        expected=[l['id'] for p in self.data['pages'] for l in p['lines'] if l['role'] not in ['running_header','editor_qa_excluded']]
        self.assertCountEqual(seen,expected)
        self.assertEqual(len(seen),len(set(seen)))

    def test_missing_image_does_not_remove_factual_evidence(self):
        data=copy.deepcopy(self.data);data['images']=[]
        result=answer('Efficiency',data,ROOT,budget=20)
        self.assertEqual(result['status'],'answered')
        self.assertIsNone(result['image'])
        self.assertIn('more than 17 times',result['answer'])
        self.assertEqual({e['page'] for e in result['evidence']},{7,8})

    def test_unrelated_arithmetic_has_no_answer(self):
        self.assertEqual(answer('10 คูณ 10 ทำไมเท่ากับ 100',self.data,ROOT)['status'],'insufficient_evidence')

    def test_thai_dataset_is_not_loadable_in_runtime(self):
        with self.assertRaisesRegex(ValueError,'English'):
            load_dataset(ROOT,language='th')

    def test_duplicate_heading_returns_choices_and_keeps_both_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'duplicate.pdf'
            with pymupdf.open() as pdf:
                for text in ['First complete description.','Second complete description.']:
                    p=pdf.new_page();p.insert_text((60,80),'Overview',fontname='hebo',fontsize=14)
                    p.insert_text((60,120),text)
                pdf.save(source)
            data=extract_document(source,root,language='en')
            result=answer('Overview',data,root)
            self.assertEqual(result['status'],'choose_section')
            self.assertEqual(len(result['choices']),2)
            self.assertEqual({c['page_start'] for c in result['choices']},{1,2})

if __name__=='__main__':unittest.main()

class SyntheticQATests(unittest.TestCase):
    def test_editor_qa_is_guidance_only_and_not_embedding_or_answer_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'source.pdf'
            with pymupdf.open() as pdf:
                p=pdf.new_page();p.insert_text((60,80),'Sorting performance',fontname='hebo',fontsize=14)
                p.insert_text((60,110),'The actual source discusses running time.')
                p.insert_text((60,150),'Semantic questions and answers',fontname='hebo')
                p.insert_text((60,180),'Q: Which method is fast? A: THIS IS EDITOR ADDED TEXT.')
                pdf.save(path)
            data=extract_document(path,root,language='en')
            self.assertNotIn('EDITOR ADDED',' '.join(c['text'] for c in data['chunks']))
            self.assertNotIn('Semantic questions and answers',' '.join(c['title'] for c in data['chunks']))
            self.assertEqual(data['query_guidance'][0]['query'],'Which method is fast?')
            result=answer('Which method is fast?',data,root)
            self.assertEqual(result['status'],'answered')
            self.assertIn('actual source',result['answer'])
            self.assertNotIn('EDITOR ADDED',result['answer'])

class ChunkBoundaryTests(unittest.TestCase):
    def test_heading_and_first_paragraph_share_small_child_without_crossing_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'boundaries.pdf'
            with pymupdf.open() as pdf:
                p=pdf.new_page()
                for y,title,body in [(80,'Efficiency','The first complete paragraph.'),(170,'Space','The second complete paragraph.')]:
                    p.insert_text((60,y),title,fontname='hebo',fontsize=12)
                    p.insert_text((60,y+25),body)
                pdf.save(path)
            data=extract_document(path,root,language='en')
            self.assertEqual(len(data['chunks']),2)
            self.assertIn('Efficiency\nThe first complete paragraph.',data['chunks'][0]['text'])
            self.assertNotIn('second',data['chunks'][0]['text'])

class RelevanceGuardTests(unittest.TestCase):
    def test_high_vector_score_alone_cannot_answer_an_unrelated_question(self):
        data=load_dataset(ROOT)
        scores={c['id']:1. for c in data['chunks']}
        result=answer('หวยคืนนี้ออกเลขอะไร',data,ROOT,dense_scores=scores)
        self.assertEqual(result['status'],'insufficient_evidence')

class NumberedHeadingTests(unittest.TestCase):
    def test_numbered_heading_is_resolved_as_parent_not_flat_keyword_hits(self):
        data=load_dataset(ROOT)
        rows=retrieve('1 Principles of sorting',data,limit=2)
        self.assertIn(33,{c['page'] for c in rows})
        self.assertTrue(all(c['retrieval_method']=='exact_heading' for c in rows))
