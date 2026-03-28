# Test cases for the falsy-numeric-or-default Semgrep rule.
# Semgrep test annotations: "ruleid" = should match, "ok" = should NOT match.

opacity = 0.5
padding_top = None
font_size = None
height = 10
value = None
data = None
settings = None
name = None

# --- Should match (true positives) ---

# ruleid: falsy-numeric-or-default
x = opacity or 1.0

# ruleid: falsy-numeric-or-default
y = padding_top or 0

# ruleid: falsy-numeric-or-default
z = font_size or 16.0

# ruleid: falsy-numeric-or-default
result = height or 100

# ruleid: falsy-numeric-or-default
neg = value or -1

# ruleid: falsy-numeric-or-default
items = sorted(nodes, key=lambda n: n.x or 0)

# ruleid: falsy-numeric-or-default
total = sum(t.font_size or 14 for t in texts)

# --- Should NOT match (true negatives) ---

# ok: falsy-numeric-or-default
name_val = name or "default"

# ok: falsy-numeric-or-default
items = data or []

# ok: falsy-numeric-or-default
config = settings or {}

# ok: falsy-numeric-or-default
safe = value if value is not None else 0.0

# ok: falsy-numeric-or-default
also_safe = 0.0 if padding_top is None else padding_top
