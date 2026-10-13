import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf
from scripts import rescan

class RescanTests(unittest.TestCase):
    def test_review_approval_does_not_survive_a_source_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'metadata').mkdir();(root/'assets/images').mkdir(parents=True)
            source=root/'current_Now.pdf'
            with pymupdf.open() as pdf:
                p=pdf.new_page();p.insert_text((60,80),'Bubble Sort compares adjacent items.')
                p.draw_rect(pymupdf.Rect(50,200,300,260));pdf.save(source)
            specs=[dict(id='figure',page=1,bbox=[50,190,320,280],title='Array',description='Array',
                image_type='visual_explanation',question_intents=['explanation'],verified=True,
                reviewed_source_sha256='different old PDF hash')]
            (root/'metadata/figure_specs.json').write_text(json.dumps(specs))
            with patch.object(rescan,'ROOT',root),patch.object(rescan,'SOURCE',source):rescan.scan()
            data=json.loads((root/'metadata/dataset.json').read_text())
            self.assertFalse(data['images'][0]['verified'])

if __name__=='__main__':unittest.main()
