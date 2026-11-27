from pathlib import Path
from skyfield.api import Loader

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "ephemeris"
TARGET.mkdir(parents=True, exist_ok=True)
loader = Loader(str(TARGET))
print("Downloading or opening NASA JPL DE440s kernel. First run needs network access (~32 MB).")
kernel = loader("de440s.bsp")
print(kernel)
print(f"Ephemeris ready: {TARGET / 'de440s.bsp'}")
