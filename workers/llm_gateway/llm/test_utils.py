import pytest
from . import logger
from .utils import get_splits

def test_get_chunks():
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
    assert chunks == [('A B ', 'Alex is here.'), ('A B ', "Isn't he?"), ('D E ', 'Yes.'), ('D E ', 'He is here.'), ('J R ', " I'm here. I'll be there soon.")]
    

    # Granularity shouldn't be too low (otherwise it skips short sentences)
    granularity = 3
    chunks = get_splits(content, granularity)
    assert chunks == [('D E ', 'Yes.'), ('D E ', 'He is here.'), ('J R ', " I'm here. I'll be there soon.")]
    
    granularity = 100
    chunks = get_splits(content, granularity)
    assert chunks == [('A B ', "Alex is here. Isn't he?"), ('D E ', 'Yes. He is here.'), ('J R ', "I'm here. I'll be there soon.")]

    # Default value for granularity == -1, and it's equivalent to have no granularity
    chunks = get_splits(content, granularity)
    assert chunks == [('A B ', "Alex is here. Isn't he?"), ('D E ', 'Yes. He is here.'), ('J R ', "I'm here. I'll be there soon.")]

