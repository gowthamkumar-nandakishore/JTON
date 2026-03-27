import jton

# Test old format
old = '[: name, age; "Alice", 30; "Bob", 25 ]'
try:
    print("Old parses:", jton.loads(old))
except Exception as e:
    print("Old FAILS:", e)

# Test new format
new_fmt = '[2: name, age; "Alice", 30; "Bob", 25 ]'
try:
    print("New parses:", jton.loads(new_fmt))
except Exception as e:
    print("New FAILS:", e)

# Test format_hint
print("Format hint:", jton.format_hint())

# Check version
print("Version:", jton.__version__)
