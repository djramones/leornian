"""Utility functions"""

import random


def generate_reference_code(length=9):
    """Generate a human-friendly reference code."""
    choices = "CDFGHJKMNPQRTVWXYZ234679"
    return "".join([random.choice(choices) for _ in range(length)])
