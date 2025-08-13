def test_sse_terminals_constant():
    from innerloop.api.sse import SSE_TERMINALS

    assert {"finished", "failed", "cancelled"}.issubset(SSE_TERMINALS)
