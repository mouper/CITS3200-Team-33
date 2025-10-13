from allostasis import AllostaticRegulator

def test_regulator_adjusts_over_time():
    reg = AllostaticRegulator(initial_strength=0.8)
    reg.update(success=True)
    new_strength = reg.get_strength()
    assert new_strength != 0.8
