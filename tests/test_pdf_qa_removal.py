import tempfile,unittest
from pathlib import Path
import pymupdf
from scripts.remove_pdf_editor_qa import redact_qa,verify_edit

class PdfQaRemovalTests(unittest.TestCase):
    def test_runtime_pdf_has_no_editor_qa_blocks_and_question_routes_survive(self):
        from services.ingest import load_dataset
        root=Path(__file__).resolve().parents[1]
        with pymupdf.open(root/'book_data/Cormen_Basic_Sorting_100_Pages.pdf') as pdf:
            self.assertEqual(len(pdf),100)
            self.assertNotIn('Semantic questions and answers',''.join(p.get_text() for p in pdf))
        data=load_dataset(root)
        self.assertEqual(len(data['query_guidance']),113)
        self.assertEqual(data['exclusions']['editor_qa_headings'],0)
        self.assertFalse(any('Semantic questions and answers' in c['text'] for c in data['chunks']))

    def test_removal_keeps_other_text_graphics_and_page_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'before.pdf';output=Path(tmp)/'after.pdf'
            with pymupdf.open() as pdf:
                p=pdf.new_page(width=600,height=800)
                p.insert_text((60,70),'Retained explanation')
                p.insert_textbox(pymupdf.Rect(60,100,500,160),'Semantic questions and answers\nQ: A question? A: An answer.',fontsize=11)
                p.draw_rect(pymupdf.Rect(60,200,300,260),color=(0,0,0))
                p.insert_text((70,230),'Retained diagram label')
                pdf.save(source)
            plan=redact_qa(source,output)
            self.assertEqual(len(plan),1)
            report=verify_edit(source,output,plan)
            self.assertEqual(report['outside_removal_pixels_changed'],0)
            with pymupdf.open(output) as pdf:
                self.assertEqual(len(pdf),1)
                self.assertNotIn('Semantic questions',pdf[0].get_text())
                self.assertNotIn('A question',pdf[0].get_text())
                self.assertIn('Retained diagram label',pdf[0].get_text())
