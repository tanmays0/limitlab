from limitlab_limiter.algorithms.refill import refill_tokens, try_consume

def test_refill_caps_at_capacity():
    tokens, _ = refill_tokens(9.0, 0, 10_000, capacity=10.0, rate=1.0)
    assert tokens == 10.0

def test_refill_adds_by_elapsed_rate():
    tokens, ts = refill_tokens(0.0, 0, 5_000, capacity=10.0, rate=1.0)
    assert tokens == 5.0
    assert ts == 5_000

def test_consume_allows_and_debits():
    ok, remaining, retry = try_consume(5.0, 10.0, 1.0, 2, debit=True)
    assert ok is True
    assert remaining == 3.0
    assert retry == 0

def test_check_does_not_debit():
    ok, remaining, retry = try_consume(5.0, 10.0, 1.0, 2, debit=False)
    assert ok is True
    assert remaining == 5.0
    assert retry == 0

def test_reject_when_insufficient_no_partial():
    ok, remaining, retry = try_consume(1.0, 10.0, 1.0, 3, debit=True)
    assert ok is False
    assert remaining == 1.0
    assert retry >= 1

def test_remaining_never_negative_on_exact():
    ok, remaining, _ = try_consume(2.0, 10.0, 1.0, 2, debit=True)
    assert ok is True
    assert remaining == 0.0
