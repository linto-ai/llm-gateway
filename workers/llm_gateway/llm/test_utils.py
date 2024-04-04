import pytest
from . import logger
from .utils import get_splits, get_dialogs


def test_get_splits():
    """
        Tesing get_split only
    """
    content = (
        "A B : Alex is here. Isn't he?\n"
        "D E : Yes. He is here.\n"
        "J R : I'm here. I'll be there soon.\n"
    )


    granularity = 6
    chunks = get_splits(content, granularity)
    assert chunks == [('A B ', 'Alex is here.'), ('A B ', "Isn't he?"), ('D E ', 'Yes.'), ('D E ', 'He is here.'), ('J R ', "I'm here."), ('J R ', "I'll be there soon.")]

    # The algorithm always try to add the last sentence (even if there is no place)
    granularity = 5
    chunks = get_splits(content, granularity)
    print(chunks)
    assert chunks == [('A B ', 'Alex is here.'), ('A B ', "Isn't he?"), ('D E ', 'Yes.'), ('D E ', 'He is here.'), ('J R ', " I'm here. I'll be there soon.")]

    # Granularity shouldn't be too low (otherwise it skips short sentences)
    granularity = 3
    chunks = get_splits(content, granularity)
    assert chunks == [('D E ', 'Yes.'), ('D E ', 'He is here.'), ('J R ', " I'm here. I'll be there soon.")]

    # Granularity is big enough to not split the speeches
    granularity = 100
    chunks = get_splits(content, granularity)
    assert chunks == [('A B ', "Alex is here. Isn't he?"), ('D E ', 'Yes. He is here.'), ('J R ', "I'm here. I'll be there soon.")]

    # Default value for granularity == -1, and it's equivalent to have no granularity
    chunks = get_splits(content, granularity)
    assert chunks == [('A B ', "Alex is here. Isn't he?"), ('D E ', 'Yes. He is here.'), ('J R ', "I'm here. I'll be there soon.")]


def test_get_dialogs():
    """
        Tesing get_split and get_dialogs together
    """
    content = (
        "A B : Alex is here. Isn't he?\n"
        "D E : Yes. He is here.\n"
        "J R : I'm here. I'll be there soon.\n"
    )
    granularity = 6
    chunks = get_splits(content, granularity)

    max_new_speeches = 4
    dialogs = get_dialogs(chunks, max_new_speeches)
    assert dialogs == ["A B  : Alex is here.\nA B  : Isn't he?\nD E  : Yes.\nD E  : He is here.\n", "J R  : I'm here.\nJ R  : I'll be there soon.\n"]
    
    max_new_speeches = 2
    dialogs = get_dialogs(chunks, max_new_speeches)
    assert dialogs == ["A B  : Alex is here.\nA B  : Isn't he?\n", 'D E  : Yes.\nD E  : He is here.\n', "J R  : I'm here.\nJ R  : I'll be there soon.\n"]

    # Default max_new_speeches == -1, and in this case function will return just one big dialog
    dialogs = get_dialogs(chunks)
    assert dialogs == ["A B  : Alex is here.\nA B  : Isn't he?\nD E  : Yes.\nD E  : He is here.\nJ R  : I'm here.\nJ R  : I'll be there soon.\n"]