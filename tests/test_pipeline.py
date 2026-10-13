import copy
import tempfile
import unittest
from pathlib import Path
import pymupdf

try:
    from services import ingest, retrieval, images, answering, context
except ImportError:
    ingest = retrieval = images = answering = context = None


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(ingest, 'New source-grounded pipeline is not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root / 'source.pdf'
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((60,80), 'Bubble Sort')
            page.insert_text((60,110), 'Bubble Sort compares adjacent items and swaps inverted pairs.')
            page.insert_text((60,145), 'A strict comparison preserves the order of equal keys.')
            page = pdf.new_page()
            page.insert_text((60,80), 'Counting Sort')
            page.insert_text((60,110), 'Counting Sort counts integer keys before placing output.')
            pdf.save(source)
        self.data = ingest.extract_document(source, self.root)
        self.data['images'] = [dict(id='explain', file='explain.webp', topic='bubble',
            kind='diagram',image_type='visual_explanation', question_intents=['explanation', 'steps'],
            linked_chunk_ids=[c['id'] for c in self.data['chunks'] if c['page']==1],
            page=1, bbox=[50,90,500,150], verified=True, source_sha256=self.data['document']['sha256'])]
        from PIL import Image
        Image.new('RGB',(100,100),'white').save(self.root/'explain.webp')

    def test_evidence_has_reproducible_page_offsets_and_coordinates(self):
        for c in self.data['chunks']:
            page=self.data['pages'][c['page']-1]
            self.assertEqual(c['text'],page['text'][c['char_start']:c['char_end']])
            self.assertTrue(c['line_ids'])
            self.assertEqual(len(c['bbox']),4)
        self.assertEqual(self.data['document']['page_count'],2)

    def test_selects_linked_explanation_instead_of_exact_answer(self):
        chunk=next(c for c in self.data['chunks'] if 'compares adjacent' in c['text'])
        exact=copy.deepcopy(self.data['images'][0]);exact.update(id='answer',image_type='exact_answer',question_intents=['fact'])
        self.data['images'].insert(0,exact)
        got=images.select_image('ช่วยอธิบาย Bubble Sort', [chunk], self.data)
        self.assertEqual(got['id'],'explain')

    def test_wrong_topic_unverified_and_unlinked_images_are_rejected(self):
        bubble=next(c for c in self.data['chunks'] if c['topic']=='bubble')
        for change in [dict(topic='counting'),dict(verified=False),dict(linked_chunk_ids=[]),dict(source_sha256='old')]:
            data=copy.deepcopy(self.data);data['images'][0].update(change)
            self.assertIsNone(images.select_image('อธิบาย Bubble Sort',[bubble],data))

    def test_outside_dataset_refuses_but_missing_image_keeps_answer(self):
        result=answering.answer('10 คูณ 10 ทำไมเท่ากับ 100',self.data,self.root)
        self.assertEqual(result['status'],'insufficient_evidence')
        data=copy.deepcopy(self.data);data['images']=[]
        result=answering.answer('อธิบาย Bubble Sort',data,self.root)
        self.assertEqual(result['status'],'answered')
        self.assertTrue(result['evidence'])
        self.assertIsNone(result['image'])

    def test_answer_is_source_text_and_does_not_cross_topics(self):
        result=answering.answer('อธิบาย Bubble Sort',self.data,self.root)
        self.assertEqual(result['status'],'answered')
        self.assertTrue(result['image'])
        for e in result['evidence']:
            self.assertEqual(e['topic'],'bubble')
            self.assertIn(e['text'],self.data['pages'][e['page']-1]['text'])
        self.assertNotIn('counts integer',result['answer'])

    def test_budget_skips_complete_oversized_evidence_instead_of_cutting(self):
        chunks=[dict(id='long',text='x '*500),dict(id='short',text='short complete sentence.')]
        got=context.select_evidence(chunks,budget=80,count_tokens=lambda t:len(t))
        self.assertEqual([c['id'] for c in got],['short'])
        self.assertEqual(got[0]['text'],'short complete sentence.')

    def test_query_preserves_original_and_normalizes_common_variants(self):
        plan=retrieval.plan_query('bubbel sort tam ngai')
        self.assertEqual(plan['original'],'bubbel sort tam ngai')
        self.assertEqual(plan['topics'],['bubble'])
        self.assertEqual(plan['intent'],'explanation')

    def test_tampered_source_or_evidence_is_rejected(self):
        data=copy.deepcopy(self.data)
        data['chunks'][0]['text']='invented answer'
        with self.assertRaises(ValueError):
            ingest.validate_dataset(data,self.root)
        data=copy.deepcopy(self.data)
        (self.root/data['document']['file']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            ingest.validate_dataset(data,self.root)

if __name__=='__main__': unittest.main()

class MultipleCropTests(unittest.TestCase):
    def test_two_figures_on_a_page_do_not_leak_graphic_labels_into_text(self):
        self.assertIsNotNone(ingest)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.pdf'
            with pymupdf.open() as pdf:
                p=pdf.new_page()
                p.insert_text((60,80),'Bubble Sort compares adjacent records.')
                p.insert_text((60,200),'FIRST DIAGRAM LABEL')
                p.insert_text((60,300),'SECOND DIAGRAM LABEL')
                pdf.save(source)
            specs=[dict(page=1,bbox=[50,180,400,220]),dict(page=1,bbox=[50,280,400,320])]
            data=ingest.extract_document(source,root,specs)
            text='\n'.join(c['text'] for c in data['chunks'])
            self.assertIn('compares adjacent',text)
            figure_labels=[c for c in data['chunks'] if 'FIRST DIAGRAM LABEL' in c['text'] or 'SECOND DIAGRAM LABEL' in c['text']]
            self.assertEqual([c['kind'] for c in figure_labels],['figure_label','figure_label'])
            prose='\n'.join(c['text'] for c in data['chunks'] if c['kind'] not in ('table','figure_label'))
            self.assertNotIn('FIRST DIAGRAM',prose)
            self.assertNotIn('SECOND DIAGRAM',prose)
            self.assertIn('FIRST DIAGRAM',text)
