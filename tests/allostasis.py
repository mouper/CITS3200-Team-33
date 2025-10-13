class AllostaticRegulator:
    """
    Small stand-in for an allostatic regulation model.
    Tracks a single "strength" value in [0, 1] and nudges it
    up on success and down on failure with a gentle step.
    """
    def __init__(self, initial_strength: float = 0.5, step: float = 0.02):
        self._strength = float(initial_strength)
        self._step = float(step)

    def update(self, success: bool) -> None:
        if success:
            self._strength = min(1.0, self._strength + self._step)
        else:
            self._strength = max(0.0, self._strength - self._step)

    def get_strength(self) -> float:
        return self._strength
