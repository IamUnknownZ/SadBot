import unittest
from pathlib import Path
from services.ingest import load_dataset
from app_test_support import OfflineAITestCase

ROOT=Path(__file__).resolve().parents[1]


class EvidenceGroupTests(OfflineAITestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_dataset(ROOT)
        cls.rows=[c for c in cls.data['chunks'] if c['page']==72 and any(c['text'].startswith(s)
                  for s in ['Divide:','Conquer:','Combine:','The recursion'])]

    def test_adjacent_passages_become_one_source_set_without_changing_their_text(self):
        from ui.evidence_groups import group_evidence,paginate_groups
        groups=group_evidence(self.rows,self.data)
        self.assertEqual(len(self.rows),4)
        self.assertEqual(len(groups),1)
        self.assertEqual(groups[0]['members'],self.rows)
        self.assertEqual(groups[0]['line_ids'],[f'p72-l{i}' for i in range(22,29)])
        self.assertEqual(len(paginate_groups(groups,max_units=2)),1)

    def test_section_heading_is_never_paginated_away_from_its_content(self):
        from services.answering import answer
        from ui.evidence_groups import group_evidence,paginate_groups
        for title in ['S2.2 Bubble sort: baseline and early-exit pseudocode','S6.7 Counting sort: deep questions, limits, and corpus audit']:
            evidence=answer(title,self.data,ROOT)['evidence']
            pages=paginate_groups(group_evidence(evidence,self.data))
            members=[m for group in pages[0] for m in group['members']]
            self.assertTrue(any(not (m['kind']=='heading' or (m.get('contains_heading') and len(m['line_ids'])==1)) for m in members),title)
            self.assertEqual([m['id'] for page in pages for group in page for m in group['members']],[m['id'] for m in evidence])

    def test_one_evidence_control_per_pdf_page_keeps_separate_highlights(self):
        from services.answering import answer
        from ui.evidence_groups import group_evidence,paginate_groups,page_evidence_groups
        from ui.document_viewer import pdf_payload
        evidence=answer('S2.2 Bubble sort: baseline and early-exit pseudocode',self.data,ROOT)['evidence']
        shown=paginate_groups(group_evidence(evidence,self.data))[0]
        pages=page_evidence_groups(shown,self.data)
        self.assertEqual(len(pages),1)
        self.assertEqual([m['id'] for m in pages[0]['members']],[m['id'] for g in shown for m in g['members']])
        payload=pdf_payload(ROOT,self.data,pages[0])
        self.assertGreater(len(payload['pdf_rectangles']),1)
        self.assertEqual(payload['line_ids'],pages[0]['line_ids'])

    def test_s22_has_one_page_button_in_the_app(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        for toggle in app.toggle:toggle.set_value(False)
        app.run()
        app.chat_input[0].set_value('S2.2 Bubble sort: baseline and early-exit pseudocode').run()
        self.assertFalse(app.exception)
        buttons=[b for b in app.button if b.label.startswith('ดูหลักฐาน')]
        self.assertEqual(len(buttons),1)
        self.assertIn('หน้า 37',buttons[0].label)
        buttons[0].click().run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('component_instance')),1)

    def test_gaps_pages_and_sections_are_not_highlighted_as_one_rectangle(self):
        from ui.evidence_groups import group_evidence
        self.assertEqual(len(group_evidence([self.rows[0],self.rows[-1]],self.data)),2)
        changed=dict(self.rows[1],section_id='another-section')
        self.assertEqual(len(group_evidence([self.rows[0],changed],self.data)),2)

    def test_pdf_has_one_block_highlight_for_contiguous_source_lines(self):
        from ui.document_viewer import pdf_payload
        from ui.evidence_groups import group_evidence
        group=group_evidence(self.rows,self.data)[0]
        payload=pdf_payload(ROOT,self.data,group)
        self.assertEqual(len(payload['pdf_rectangles']),1)
        self.assertEqual(payload['line_ids'],group['line_ids'])

    def test_four_adjacent_sources_have_one_button_and_one_pdf_reader(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        for toggle in app.toggle:toggle.set_value(False)
        app.run()
        app.session_state['messages']=[dict(query=dict(original='Merge Sort แบ่งข้อมูลยังไง'),status='answered',
            answer='\n\n'.join(r['text'] for r in self.rows),evidence=self.rows,image=None,steps=[],
            source_language='en',display_text={},translate_enabled=False)]
        app.run()
        self.assertFalse(app.exception)
        buttons=[b for b in app.button if b.label.startswith('ดูหลักฐาน')]
        self.assertEqual(len(buttons),1)
        self.assertIn('22–28',buttons[0].label)
        buttons[0].click().run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('component_instance')),1)


if __name__=='__main__':unittest.main()
