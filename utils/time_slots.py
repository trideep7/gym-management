"""Dropdown shaping shared by the member and trainer forms.

The canonical timing options themselves are admin-managed and stored via
services.time_slots; this module only turns a list of active labels into
selectbox options, so it stays a plain function with no database
dependency of its own.
"""

# A plain string rather than Python None: streamlit.testing.v1 can't
# simulate selecting a selectbox option whose value is None, so a None
# option would be untestable through the page tests. Translated to NULL
# on the way into the database by to_stored().
NOT_SET = "Not set"


def options_for(current, available_labels):
    """Dropdown options for a record whose slot is `current`.

    A value that isn't one of the canonical slots is kept as an option of
    its own, so opening a form and saving it can't silently rewrite a
    slot nobody meant to change -- including one that's since been
    renamed or deactivated by an admin.
    """
    options = [NOT_SET] + list(available_labels)
    if current and current not in options:
        options.insert(1, current)
    return options


def index_of(current, options):
    return options.index(current) if current in options else 0


def to_stored(selection):
    """What to persist -- "Not set" means no slot on file."""
    return None if selection == NOT_SET else selection
