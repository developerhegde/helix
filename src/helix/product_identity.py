"""Product identity manifest (LLD 00 §3).

The only code-owned source of renameable identifiers. Every other module derives
names from here; a guard test refuses the product name as a literal elsewhere.
"""

DISPLAY_NAME = "Helix"
CANONICAL_ID = "helix"

ENV_PREFIX = CANONICAL_ID.upper() + "_"
PROFILE_FILENAME = CANONICAL_ID + ".yaml"
PROFILE_ENV_VAR = ENV_PREFIX + "CLIENT_PROFILE"
BRANCH_PREFIX = CANONICAL_ID + "/"
CONTAINER_PATH_SEGMENT = CANONICAL_ID
IMAGE_NAME_PREFIX = CANONICAL_ID + "-"
