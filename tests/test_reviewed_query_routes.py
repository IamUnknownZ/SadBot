import tempfile,json,unittest
from pathlib import Path
from services.ingest import attach_reviewed_routes

class ReviewedQueryRouteTests(unittest.TestCase):
    def test_only_questions_are_restored_as_routes_and_source_must_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metadata').mkdir()
            route=dict(query='Why is it stable?',target_title='Stability',source_page=2,answer='This must never enter evidence')
            (root/'metadata/reviewed_query_routes.json').write_text(json.dumps(dict(source_sha256='current',routes=[route])))
            def data(sha):return dict(document=dict(sha256=sha),query_guidance=[],nodes=[dict(id='new-node',title='Stability',kind='subsection',page_start=2,page_end=2)])
            result=attach_reviewed_routes(data('current'),root)
            self.assertEqual(result['query_guidance'][0]['target_section_id'],'new-node')
            self.assertNotIn('answer',result['query_guidance'][0])
            self.assertEqual(attach_reviewed_routes(data('stale'),root)['query_guidance'],[])
