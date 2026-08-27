"""The gym's timetable slots, shared by the member and trainer forms.

Both pick from the same list, so a trainer's slot and a member's
preferred slot are directly comparable rather than being two sets of
free text that happen to look alike.
"""

# A plain string rather than Python None: streamlit.testing.v1 can't
# simulate selecting a selectbox option whose value is None, so a None
# option would be untestable through the page tests. Translated to NULL
# on the way into the database by to_stored().
NOT_SET = "Not set"

TIME_SLOTS = [
    "6:00 AM - 8:00 AM",
    "8:00 AM - 10:00 AM",
    "10:00 AM - 4:00 PM",
    "4:00 PM - 6:00 PM",
]


def options_for(current):
    """Dropdown options for a record whose slot is `current`.

    A value that isn't one of the canonical slots is kept as an option of
    its own, so opening a form and saving it can't silently rewrite a
    slot nobody meant to change.
    """
    options = [NOT_SET] + TIME_SLOTS
    if current and current not in options:
        options.insert(1, current)
    return options


def index_of(current, options):
    return options.index(current) if current in options else 0


def to_stored(selection):
    """What to persist -- "Not set" means no slot on file."""
    return None if selection == NOT_SET else selection
