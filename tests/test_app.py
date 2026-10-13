import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from app_test_support import OfflineAITestCase

ROOT=Path(__file__).resolve().parents[1]

class AppTests(OfflineAITestCase):
    def test_answer_with_image_and_evidence_survives_rerun(self):
        self.assertTrue((ROOT/'app.py').is_file(),'New application is not implemented')
        app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        app.toggle[0].set_value(False).run(timeout=30)
        app.chat_input[0].set_value('Bubble Sort ทีละขั้น').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['messages'][-1]['status'],'answered')
        image=app.session_state['messages'][-1]['image']['id']
        app.run(timeout=30)
        self.assertEqual(app.session_state['messages'][-1]['image']['id'],image)
        self.assertTrue(app.session_state['messages'][-1]['evidence'])
        self.assertFalse(app.exception)

if __name__=='__main__':unittest.main()
