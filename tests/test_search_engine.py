import tempfile
import unittest
from pathlib import Path

from search_engine import QueryError, SearchEngine
from search_engine.indexer import InvertedIndex
from search_engine.loader import load_documents
from search_engine.normalizer import normalize
from search_engine.query import And, Not, Or, Term, parse
from search_engine.tokenizer import tokenize, words
from search_engine.wildcard import KGramIndex

DOCS = {
    "a.txt": "Information Retrieval with an inverted index.",
    "b.txt": "Boolean retrieval: AND, OR and NOT over postings.",
    "c.txt": "Web crawlers retrieve pages. The café is closed.",
}


class LoaderTest(unittest.TestCase):
    def test_loads_txt_files_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in DOCS.items():
                Path(tmp, name).write_text(text, encoding="utf-8")
            Path(tmp, "skip.md").write_text("ignored", encoding="utf-8")
            docs = load_documents(tmp)
        self.assertEqual([d.name for d in docs], ["a.txt", "b.txt", "c.txt"])
        self.assertEqual([d.doc_id for d in docs], [0, 1, 2])

    def test_missing_folder(self):
        with self.assertRaises(FileNotFoundError):
            load_documents("does/not/exist")


class TokenizerTest(unittest.TestCase):
    def test_splits_on_punctuation_and_hyphens(self):
        self.assertEqual(words("state-of-the-art, don't stop!"), ["state", "of", "the", "art", "don't", "stop"])

    def test_keeps_offsets(self):
        tok = tokenize("  hello")[0]
        self.assertEqual((tok.start, tok.end), (2, 7))


class NormalizerTest(unittest.TestCase):
    def test_case_folding_accents_apostrophes(self):
        self.assertEqual(normalize("Retrieval"), "retrieval")
        self.assertEqual(normalize("Café"), "cafe")
        self.assertEqual(normalize("Don't"), "dont")


class IndexerTest(unittest.TestCase):
    def test_postings_and_frequencies(self):
        index = InvertedIndex()
        index.add_document(0, ["a", "b", "a"])
        index.add_document(1, ["b"])
        self.assertEqual(index.postings("a"), {0: 2})
        self.assertEqual(index.doc_ids("b"), {0, 1})
        self.assertEqual(index.vocabulary, ["a", "b"])


class QueryParserTest(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(parse("a OR b AND NOT c"), Or(Term("a"), And(Term("b"), Not(Term("c")))))

    def test_implicit_and_and_parentheses(self):
        self.assertEqual(parse("(a OR b) c"), And(Or(Term("a"), Term("b")), Term("c")))

    def test_operators_are_case_insensitive(self):
        self.assertEqual(parse("a and b"), And(Term("a"), Term("b")))

    def test_errors(self):
        for bad in ["", "a OR", "(a", "a)", "NOT"]:
            with self.subTest(query=bad), self.assertRaises(QueryError):
                parse(bad)


class WildcardTest(unittest.TestCase):
    def setUp(self):
        self.kgrams = KGramIndex(k=2)
        self.kgrams.add_terms(["retrieval", "retrieve", "relevant", "index", "xdni"])

    def test_prefix_suffix_infix(self):
        self.assertEqual(self.kgrams.expand("retriev*"), ["retrieval", "retrieve"])
        self.assertEqual(self.kgrams.expand("*dex"), ["index"])
        self.assertEqual(self.kgrams.expand("re*t"), ["relevant"])

    def test_post_filter_removes_false_positives(self):
        self.assertEqual(self.kgrams.expand("ind*x"), ["index"])

    def test_pattern_is_normalized(self):
        self.assertEqual(self.kgrams.expand("RETRIEV*"), ["retrieval", "retrieve"])


class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        for name, text in DOCS.items():
            Path(cls.tmp.name, name).write_text(text, encoding="utf-8")
        cls.engine = SearchEngine.from_directory(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def names(self, query):
        return sorted(hit.name for hit in self.engine.search(query).hits)

    def test_boolean_queries(self):
        self.assertEqual(self.names("retrieval"), ["a.txt", "b.txt"])
        self.assertEqual(self.names("retrieval AND NOT boolean"), ["a.txt"])
        self.assertEqual(self.names("index OR crawlers"), ["a.txt", "c.txt"])

    def test_query_is_normalized_like_documents(self):
        self.assertEqual(self.names("CAFE"), ["c.txt"])

    def test_wildcard(self):
        result = self.engine.search("retriev*")
        self.assertEqual(result.expansions["retriev*"], ["retrieval", "retrieve"])
        self.assertEqual(len(result.hits), 3)

    def test_highlights_point_at_matches(self):
        hit = self.engine.search("inverted").hits[0]
        self.assertEqual([hit.snippet[s:e] for s, e in hit.highlights], ["inverted"])


if __name__ == "__main__":
    unittest.main()
