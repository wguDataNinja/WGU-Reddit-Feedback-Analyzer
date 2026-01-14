import sys

sys.path.insert(0, "llm-db")

from llm_db.query_translate_stub import translate_nl_to_plan
from llm_db.sql_selector import compile_plan
from llm_db.storage import execute_readonly


DB = "llm-db/golds/data/wgu_reddit.sqlite"


def test_top_posts_score_smoke():
    plan = translate_nl_to_plan("top posts by score for D335")
    cq = compile_plan(plan)
    cols, rows = execute_readonly(DB, cq.sql, cq.params, cq.max_rows)
    assert cq.template_id.value == "top_posts_score"
    assert "post_id" in cols
    assert len(rows) > 0


def test_counts_smoke():
    plan = translate_nl_to_plan("how many posts for D335")
    cq = compile_plan(plan)
    cols, rows = execute_readonly(DB, cq.sql, cq.params, cq.max_rows)
    assert cq.template_id.value == "post_counts"
    assert cols == ["posts_count"]
    assert len(rows) == 1
    assert isinstance(rows[0][0], int)


def test_metadata_smoke():
    plan = translate_nl_to_plan("metadata")
    cq = compile_plan(plan)
    cols, rows = execute_readonly(DB, cq.sql, cq.params, cq.max_rows)
    assert cq.template_id.value == "posts_metadata"
    assert len(rows) == 1
    assert "posts_count" in cols