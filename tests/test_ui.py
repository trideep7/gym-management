import ui


def test_page_bounds_of_an_empty_list_is_a_single_empty_page():
    assert ui.page_bounds(0, 20, 1) == (1, 1, 0, 0)


def test_page_bounds_first_page_of_an_exact_multiple():
    assert ui.page_bounds(40, 20, 1) == (1, 2, 0, 20)


def test_page_bounds_last_page_of_an_exact_multiple():
    assert ui.page_bounds(40, 20, 2) == (2, 2, 20, 40)


def test_page_bounds_partial_last_page():
    assert ui.page_bounds(45, 20, 3) == (3, 3, 40, 45)


def test_page_bounds_clamps_a_page_below_one():
    assert ui.page_bounds(45, 20, 0) == (1, 3, 0, 20)


def test_page_bounds_clamps_a_page_past_the_end():
    # deleting the last row on the last page must not strand the viewer
    # on a page that no longer exists
    assert ui.page_bounds(45, 20, 9) == (3, 3, 40, 45)


def test_page_bounds_when_everything_fits_on_one_page():
    assert ui.page_bounds(5, 20, 1) == (1, 1, 0, 5)
