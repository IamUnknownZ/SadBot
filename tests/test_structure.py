import unittest
import tempfile
from pathlib import Path
import pymupdf
from services.ingest import extract_document
from services.context import token_count
from services import answering

class StructureTests(unittest.TestCase):
    def test_mixed_whitespace_font_does_not_hide_semantic_headings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'source.pdf'
            with pymupdf.open() as pdf:
                p=pdf.new_page()
                p.insert_text((60,80),'First heading',fontname='hebo')
                p.insert_text((60,100),'First complete explanation stays together.')
                p.insert_text((60,125),'Second heading',fontname='hebo')
                p.insert_text((60,145),'Second complete explanation stays separate.')
                pdf.save(path)
            data=extract_document(path,root)
            values=[c['text'] for c in data['chunks']]
            self.assertEqual(len(values),2)
            self.assertIn('First complete explanation',values[0])
            self.assertNotIn('Second complete explanation',values[0])

    def test_current_pdf_separates_bold_heading_sections_despite_regular_spaces(self):
        root=Path(__file__).resolve().parents[1]
        data=extract_document(root/'book_data/Cormen_Basic_Sorting_100_Pages.pdf',root)
        chunks=[c for c in data['chunks'] if c['page']==38 and 'Start with' in c['text']]
        self.assertTrue(chunks)
        self.assertNotIn('Explain a state',chunks[0]['text'])

    def test_small_figure_labels_do_not_make_body_prose_into_headings(self):
        root=Path(__file__).resolve().parents[1]
        data=extract_document(root/'book_data/Cormen_Basic_Sorting_100_Pages.pdf',root)
        fake=[n for n in data['nodes'] if n['kind']=='subsection' and n['source_page']==74 and
              (n['title'].startswith(('trated in Figure','At the start of each','We must show','loop of lines','Initialization: Prior','subarray A[')) or n['title']=='loop invariant:')]
        self.assertEqual(fake,[])

    def test_exercises_heading_owns_its_numbered_questions(self):
        root=Path(__file__).resolve().parents[1]
        data=extract_document(root/'book_data/Cormen_Basic_Sorting_100_Pages.pdf',root)
        nodes={n['id']:n for n in data['nodes']}
        exercises=[n for n in data['nodes'] if n['title']=='Exercises' and n['kind']=='subsection']
        self.assertEqual(len(exercises),6)
        for n in exercises:
            numbered=[nodes[c] for c in n['child_ids'] if nodes[c]['kind']=='subsection']
            self.assertTrue(numbered,n['source_page'])
            self.assertTrue(all(set(c['chunk_ids']).issubset(n['chunk_ids']) for c in numbered))

    def test_context_counts_thai_with_a_named_tokenizer(self):
        self.assertLess(token_count('สวัสดีครับ'),len('สวัสดีครับ'.encode('utf-8')))
        self.assertGreater(token_count('สวัสดีครับ'),0)

if __name__=='__main__':unittest.main()
