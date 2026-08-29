import json, os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.environ.get("SEED_DIR", os.path.join(_REPO, "seed", "data"))

def load(name):
    with open(os.path.join(_DATA, name)) as f:
        return json.load(f)
