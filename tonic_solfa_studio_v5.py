"""Compatibility wrapper for the legacy `tonic_solfa_studio_v5` entry point.

Recommended main file: `tonic_solfa_studio.py`
"""

from tonic_solfa_studio import *  # noqa: F401,F403
from tonic_solfa_studio import TonicSolfaStudio, main


if __name__ == "__main__":
    main()

