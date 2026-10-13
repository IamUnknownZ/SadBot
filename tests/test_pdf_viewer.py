import unittest
import base64
from pathlib import Path
import pymupdf
from services.ingest import load_dataset
from services.answering import answer
from ui.document_viewer import pdf_payload
from ui.evidence_groups import highlight_regions
ROOT=Path(__file__).resolve().parents[1]

class PdfViewerTests(unittest.TestCase):
    def test_payload_is_actual_selected_source_page_and_precise_lines(self):
        for lang in ['en']:
            data=load_dataset(ROOT,language=lang)
            c=answer('Bubble Sort ทีละขั้น',data,ROOT)['evidence'][0]
            payload=pdf_payload(ROOT,data,c)
            with pymupdf.open(stream=base64.b64decode(payload['pdf']),filetype='pdf') as pdf:
                self.assertEqual(len(pdf),1)
                with pymupdf.open(ROOT/data['document']['file']) as source:
                    self.assertEqual(pdf[0].get_text(),source[c['page']-1].get_text())
            self.assertEqual(payload['source_page'],c['page'])
            expected=highlight_regions([l for l in data['pages'][c['page']-1]['lines'] if l['id'] in c['line_ids']])
            self.assertEqual(payload['rectangles'],expected)
            self.assertGreater(len(expected),0)

    def test_cropped_source_coordinates_round_trip_to_original_lines(self):
        data=load_dataset(ROOT)
        c=next(c for c in answer('Efficiency',data,ROOT)['evidence'] if c['page']==8)
        payload=pdf_payload(ROOT,data,c)
        with pymupdf.open(stream=base64.b64decode(payload['pdf']),filetype='pdf') as pdf:
            for original,pdf_box in zip(payload['rectangles'],payload['pdf_rectangles']):
                restored=pymupdf.Rect(pdf_box)*pdf[0].transformation_matrix
                for actual,expected in zip(restored,original):
                    self.assertAlmostEqual(actual,expected,places=3)

if __name__=='__main__':unittest.main()
