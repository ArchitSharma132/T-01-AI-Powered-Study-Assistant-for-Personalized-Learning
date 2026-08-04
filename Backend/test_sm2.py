from app.services.scheduler import sm2


def test_first_correct():
    interval, ef, reps = sm2(5, 0, 2.5, 0)
    assert interval == 1
    assert reps == 1
    assert round(ef, 2) == 2.6


def test_second_correct():
    interval, ef, reps = sm2(5, 1, 2.6, 1)
    assert interval == 6
    assert reps == 2
    assert round(ef, 2) == 2.7


def test_third_correct():
    interval, ef, reps = sm2(5, 2, 2.7, 6)
    assert interval == 16
    assert reps == 3


def test_incorrect_resets():
    interval, ef, reps = sm2(1, 3, 2.5, 15)
    assert interval == 1
    assert reps == 0
    assert ef < 2.5


def test_hesitant_correct():
    interval, ef, reps = sm2(3, 0, 2.5, 0)
    assert interval == 1
    assert reps == 1
    assert ef < 2.5


def test_ef_floor():
    _, ef, _ = sm2(0, 0, 1.3, 0)
    assert ef == 1.3


def test_after_reset():
    interval, ef, reps = sm2(5, 0, 1.7, 1)
    assert interval == 1
    assert reps == 1
    assert ef >= 1.7
