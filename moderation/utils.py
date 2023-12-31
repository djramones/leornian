import random
from datetime import datetime, timezone


def generate_date_based_reference_code():
    """Generate a reference code with date and random components."""
    code = datetime.now(timezone.utc).isoformat()[:10].replace("-", "")
    code += "-"
    choices = "CDFGHJKMNPQRTVWXYZ234679"
    code += "".join([random.choice(choices) for _ in range(8)])
    return code
