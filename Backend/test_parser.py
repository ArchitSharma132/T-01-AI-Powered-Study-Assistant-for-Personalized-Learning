from app.services.parser import parse_mcq, parse_tf, parse_short


def test_parse_mcq_clean():
    raw = '[{"question":"What is X?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct":"A","explanation":"Because","difficulty":"easy"}]'
    result = parse_mcq(raw)
    assert len(result) == 1
    assert result[0].correct == "A"


def test_parse_mcq_with_markdown():
    raw = '```json\n[{"question":"Q?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct":"B","explanation":"E","difficulty":"medium"}]\n```'
    result = parse_mcq(raw)
    assert len(result) == 1


def test_parse_mcq_invalid_correct():
    raw = '[{"question":"Q?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct":"E","explanation":"E","difficulty":"easy"}]'
    result = parse_mcq(raw)
    assert len(result) == 0


def test_parse_mcq_wrong_option_count():
    raw = '[{"question":"Q?","options":{"A":"a","B":"b"},"correct":"A","explanation":"E","difficulty":"easy"}]'
    result = parse_mcq(raw)
    assert len(result) == 0


def test_parse_mcq_dedup():
    raw = '[{"question":"Same?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct":"A","explanation":"E","difficulty":"easy"},{"question":"Same?","options":{"A":"a","B":"b","C":"c","D":"d"},"correct":"A","explanation":"E","difficulty":"easy"}]'
    result = parse_mcq(raw)
    assert len(result) == 1


def test_parse_tf_clean():
    raw = '[{"question":"Water boils at 100C","correct":true,"explanation":"Yes","difficulty":"easy"}]'
    result = parse_tf(raw)
    assert len(result) == 1
    assert result[0].correct is True


def test_parse_short_clean():
    raw = '[{"question":"What is X?","model_answer":"X is Y","key_terms":["X","Y"],"difficulty":"medium"}]'
    result = parse_short(raw)
    assert len(result) == 1
    assert result[0].key_terms == ["X", "Y"]


def test_parse_empty():
    assert parse_mcq("") == []
    assert parse_tf("") == []
    assert parse_short("") == []


def test_parse_garbage():
    assert parse_mcq("not json at all") == []
