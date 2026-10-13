import tempfile
import unittest
from pathlib import Path
try:
    from services import vectors
except ImportError:
    vectors=None

class VectorTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(vectors,'Dense index service is missing')
        self.data={'document':{'sha256':'current'},'chunks':[
            {'id':'a','text':'adjacent exchanges','curriculum_status':'primary'},
            {'id':'b','text':'count integer keys','curriculum_status':'primary'}]}

    def test_dense_search_ranks_meaning_and_rejects_stale_text(self):
        index=vectors.build_index(self.data,embed=lambda texts,task:[[1.,0.],[0.,1.]])
        scores=vectors.search_index('nearby swapping',self.data,index,embed=lambda texts,task:[[1.,0.]])
        self.assertGreater(scores['a'],scores['b'])
        self.data['chunks'][0]['text']='different source'
        with self.assertRaises(ValueError):
            vectors.search_index('query',self.data,index,embed=lambda texts,task:[[1.,0.]])

    def test_incomplete_and_nonfinite_vectors_cannot_be_published(self):
        for rows in [[],[[1.,0.]],[[float('nan'),0.],[0.,1.]]]:
            with self.assertRaises(ValueError):
                vectors.build_index(self.data,embed=lambda texts,task:rows)

if __name__=='__main__':unittest.main()
