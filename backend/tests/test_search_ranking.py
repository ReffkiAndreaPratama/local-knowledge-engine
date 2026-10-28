"""Search query safety and hybrid ranking tests."""
import pytest

from app.search.fts import build_fts_query
from app.search.hybrid import deduplicate_by_document, reciprocal_rank_fusion


def test_empty_query_returns_none():
    assert build_fts_query("") is None
    assert build_fts_query("   ") is None
    assert build_fts_query(None) is None


def test_terms_are_quoted_and_and_ed():
    expression = build_fts_query("database connection")
    assert expression == '"database"* AND "connection"*'


def test_quotes_are_stripped_to_prevent_injection():
    expression = build_fts_query('foo" OR 1=1 --')
    assert expression is not None
    # Every user term must be inside a quoted FTS5 string, so quotes are balanced
    assert expression.count('"') % 2 == 0
    # No unquoted comment token can reach the SQL layer
    assert not expression.strip().startswith("--")


def test_special_fts_characters_are_removed():
    expression = build_fts_query("NEAR(a b) ^ *")
    assert expression is not None
    assert "^" not in expression
    assert "(" not in expression or expression.count("(") == 0


def test_phrase_query_is_preserved():
    expression = build_fts_query('"database connection"')
    assert expression == '"database connection"'


def test_boolean_operators_supported():
    expression = build_fts_query("database AND migration")
    assert expression is not None
    assert "AND" in expression


def test_rrf_is_deterministic():
    first = ["a", "b", "c"]
    second = ["b", "a", "d"]
    result_one = reciprocal_rank_fusion([first, second], k=60)
    result_two = reciprocal_rank_fusion([first, second], k=60)
    assert result_one == result_two
    assert [item[0] for item in result_one] == ["a", "b", "c", "d"]


def test_rrf_rewards_documents_found_by_both():
    keyword_only = ["k1", "shared", "k2"]
    semantic_only = ["s1", "s2", "shared"]
    fused = dict(reciprocal_rank_fusion([keyword_only, semantic_only], k=60))
    assert fused["shared"] > fused["k1"]
    assert fused["shared"] > fused["s1"]


def test_rrf_weights_change_ordering():
    keyword = ["k1", "k2"]
    semantic = ["s1", "s2"]
    fused = dict(
        reciprocal_rank_fusion([keyword, semantic], k=60, weights=[1.0, 5.0])
    )
    assert fused["s1"] > fused["k1"]


def test_rrf_rejects_mismatched_weights():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], weights=[1.0, 2.0])


def test_deduplicate_by_document():
    ranked = [("c1", 1.0), ("c2", 0.9), ("c3", 0.8), ("c4", 0.7)]
    chunk_to_doc = {"c1": "d1", "c2": "d1", "c3": "d1", "c4": "d2"}
    kept = deduplicate_by_document(ranked, chunk_to_doc, max_per_document=2)
    assert [c for c, _ in kept] == ["c1", "c2", "c4"]
