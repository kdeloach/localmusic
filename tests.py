import unittest
from catalog import SearchTerm
from catalog import SearchTermSql

class TestSearchTerm(unittest.TestCase):
    def test10(self):
        tokens = list(SearchTerm('a'))
        self.assertEqual(tokens, [('POSITIVE', ('TERM', 'a'))])

    def test20(self):
        tokens = list(SearchTerm('-a'))
        self.assertEqual(tokens, [('NEGATIVE', ('POSITIVE', ('TERM', 'a')))])

    def test30(self):
        tokens = list(SearchTerm('a -a'))
        self.assertEqual(tokens, [('POSITIVE', ('TERM', 'a')),
                                  ('NEGATIVE', ('POSITIVE', ('TERM', 'a')))])
                                  
    def test31(self):
        tokens = list(SearchTerm('-a a'))
        self.assertEqual(tokens, [('NEGATIVE', ('POSITIVE', ('TERM', 'a'))),
                                  ('POSITIVE', ('TERM', 'a'))])

    def test40(self):
        tokens = list(SearchTerm('"a b"'))
        self.assertEqual(tokens, [('POSITIVE', ('EXACT', [('TERM', 'a'),
                                                          ('TERM', 'b')]))])
                                                          
    def test41(self):
        tokens = list(SearchTerm("\"a\\\"b\""))
        self.assertEqual(tokens, [('POSITIVE', ('EXACT', [('TERM', 'a"b')]))])
        
    def test42(self):
        tokens = list(SearchTerm("'a\\\'b'"))
        self.assertEqual(tokens, [('POSITIVE', ('EXACT', [('TERM', 'a\'b')]))])
        
    def test43(self):
        tokens = list(SearchTerm("\"a'b\""))
        self.assertEqual(tokens, [('POSITIVE', ('EXACT', [('TERM', "a'b")]))])
                                                          
    def test50(self):
        tokens = list(SearchTerm('-"a b"'))
        self.assertEqual(tokens, [('NEGATIVE', ('POSITIVE', ('EXACT', [('TERM', 'a'),
                                                                       ('TERM', 'b')])))])
                                                                       
    def test60(self):
        tokens = list(SearchTerm('a -"b c" "d" -e f'))
        self.assertEqual(tokens, [('POSITIVE', ('TERM', 'a')),
                                  ('NEGATIVE', ('POSITIVE', ('EXACT', [('TERM', 'b'),
                                                                       ('TERM', 'c')]))),
                                  ('POSITIVE', ('EXACT', [('TERM', 'd')])),
                                  ('NEGATIVE', ('POSITIVE', ('TERM', 'e'))),
                                  ('POSITIVE', ('TERM', 'f'))])
                                  
    def test70(self):
        tokens = list(SearchTerm(''))
        self.assertEqual(tokens, [])
        

if __name__ == '__main__':
    unittest.main()