import unittest
from catalog import SearchTerm
from catalog import SearchTermSql

class SearchTermTest(unittest.TestCase):

    def test_positive(self):
        tokens = list(SearchTerm('a'))
        self.assertEqual(tokens, [('POSITIVE', ('TERM', 'a'))])

    def test_negative(self):
        tokens = list(SearchTerm('-a'))
        self.assertEqual(tokens, [('NEGATIVE', ('POSITIVE', ('TERM', 'a')))])

    def test_positive_negative(self):
        tokens = list(SearchTerm('a -a'))
        self.assertEqual(tokens, [('POSITIVE', ('TERM', 'a')),
                                  ('NEGATIVE', ('POSITIVE', ('TERM', 'a')))])

    def test_negative_positive(self):
        tokens = list(SearchTerm('-a a'))
        self.assertEqual(tokens, [('NEGATIVE', ('POSITIVE', ('TERM', 'a'))),
                                  ('POSITIVE', ('TERM', 'a'))])

    def test_multiple(self):
        tokens = list(SearchTerm('"a b"'))
        self.assertEqual(tokens, [('POSITIVE', ('EXACT', [('TERM', 'a'),
                                                          ('TERM', 'b')]))])

    def test_escaping0(self):
        tokens = list(SearchTerm("\"a\\\"b\""))
        self.assertEqual(tokens, [('POSITIVE', ('EXACT', [('TERM', 'a"b')]))])

    def test_escaping1(self):
        tokens = list(SearchTerm("'a\\\'b'"))
        self.assertEqual(tokens, [('POSITIVE', ('EXACT', [('TERM', 'a\'b')]))])

    def test_escaping2(self):
        tokens = list(SearchTerm("\"a'b\""))
        self.assertEqual(tokens, [('POSITIVE', ('EXACT', [('TERM', "a'b")]))])

    def test_negative_exact(self):
        tokens = list(SearchTerm('-"a b"'))
        self.assertEqual(tokens, [('NEGATIVE', ('POSITIVE', ('EXACT', [('TERM', 'a'),
                                                                       ('TERM', 'b')])))])

    def test_mixed(self):
        tokens = list(SearchTerm('a -"b c" "d" -e f'))
        self.assertEqual(tokens, [('POSITIVE', ('TERM', 'a')),
                                  ('NEGATIVE', ('POSITIVE', ('EXACT', [('TERM', 'b'),
                                                                       ('TERM', 'c')]))),
                                  ('POSITIVE', ('EXACT', [('TERM', 'd')])),
                                  ('NEGATIVE', ('POSITIVE', ('TERM', 'e'))),
                                  ('POSITIVE', ('TERM', 'f'))])

    def test_empty(self):
        tokens = list(SearchTerm(''))
        self.assertEqual(tokens, [])
