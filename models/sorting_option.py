from enum import Enum, auto


class SortBy(Enum):
    """
        Sort by options.
    """
    SYMBOL = auto()
    PRICE = auto()
    VOLUME = auto()
    CHANGE = auto()
    CHANGE_PERCENT = auto()


class SortOrder(Enum):
    """
        Sort order options.
    """
    ASCENDING = False
    DESCENDING = True


class SortingOption:
    def __init__(self, sort_by: SortBy, sort_order: SortOrder):
        self.sort_by = sort_by
        self.sort_order = sort_order


if __name__ == "__main__":
    sortOrder = SortOrder.DESCENDING
    my_list = [5, 10, 1, 3, 2]
    print(sorted(my_list, reverse=sortOrder.value))
