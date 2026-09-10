from utils import time_slots

SLOTS = ["6:00 AM - 8:00 AM", "8:00 AM - 10:00 AM", "10:00 AM - 4:00 PM", "4:00 PM - 6:00 PM"]


def test_options_start_with_not_set_then_the_given_slots():
    assert time_slots.options_for(None, SLOTS) == [time_slots.NOT_SET] + SLOTS


def test_a_recognised_current_value_does_not_get_duplicated():
    assert time_slots.options_for("8:00 AM - 10:00 AM", SLOTS) == [time_slots.NOT_SET] + SLOTS


def test_an_unrecognised_current_value_is_kept_as_an_option():
    # otherwise the next save silently rewrites it to whichever slot
    # happens to sort first
    options = time_slots.options_for("8am-10am", SLOTS)
    assert "8am-10am" in options
    assert set(SLOTS) <= set(options)


def test_index_of_finds_the_current_value():
    options = time_slots.options_for("10:00 AM - 4:00 PM", SLOTS)
    assert options[time_slots.index_of("10:00 AM - 4:00 PM", options)] == "10:00 AM - 4:00 PM"


def test_index_of_an_unrecognised_value_selects_it_rather_than_the_first_slot():
    options = time_slots.options_for("8am-10am", SLOTS)
    assert options[time_slots.index_of("8am-10am", options)] == "8am-10am"


def test_index_of_no_value_selects_not_set():
    options = time_slots.options_for(None, SLOTS)
    assert options[time_slots.index_of(None, options)] == time_slots.NOT_SET


def test_not_set_is_stored_as_no_value():
    assert time_slots.to_stored(time_slots.NOT_SET) is None


def test_a_real_slot_is_stored_as_itself():
    assert time_slots.to_stored("4:00 PM - 6:00 PM") == "4:00 PM - 6:00 PM"


def test_options_for_with_no_available_labels_still_offers_not_set():
    # an admin who has deactivated every timing option shouldn't break
    # the form -- there's simply nothing but "Not set" to choose from
    assert time_slots.options_for(None, []) == [time_slots.NOT_SET]
