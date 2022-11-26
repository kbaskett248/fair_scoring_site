import sys
from pathlib import Path

directory = Path(__file__).parent
_mod = sys.modules[__name__]

for f in directory.iterdir():
    if f.is_dir():
        continue

    fixture_name = f.name.replace(".", "_")
    with open(f, "r") as file_ptr:
        fixture_contents = file_ptr.read()

    setattr(_mod, fixture_name, fixture_contents)
