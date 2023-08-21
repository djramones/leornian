"""Utility functions"""

from collections import namedtuple
import random


ChoiceTags = namedtuple("ChoiceTags", ["bg", "icon"])


def generate_reference_code(length=9):
    """Generate a human-friendly reference code."""
    choices = "CDFGHJKMNPQRTVWXYZ234679"
    return "".join([random.choice(choices) for _ in range(length)])


LOREM_IPSUM_WORDS = (
    "eu tortor hac eleifend nunc risus enim sollicitudin platea quis "
    "phasellus magna orci sagittis placerat condimentum habitant fermentum "
    "consequat id sit praesent scelerisque maecenas pretium venenatis "
    "tincidunt sapien est sodales netus semper suscipit auctor mi a non "
    "volutpat in hendrerit consectetur massa habitasse vestibulum ultrices "
    "proin ornare ultricies pellentesque sed morbi dictumst iaculis duis "
    "viverra cursus elit posuere integer ac turpis blandit nisi fames aenean "
    "pharetra sem dui congue mattis urna quisque cras dignissim diam "
    "malesuada amet purus justo tempus nisl nibh aliquet adipiscing nulla "
    "senectus et metus lectus eros vitae gravida at aliquam tellus egestas "
    "tristique mauris eget ut"
)
LOREM_IPSUM_WORDS = LOREM_IPSUM_WORDS.split()


def generate_lorem_ipsum(
    start_with_lorem=True,
    min_words=10,
    max_words=40,
    rich=False,
):
    """Generate random dummy text with optional Markdown rich formatting."""

    num_words = random.randint(min_words, max_words)
    format_choices = ("{}", "*{}*", "**{}**")
    format_weights = (6, 1, 1)

    word_list = []
    for _ in range(num_words):
        word = random.choice(LOREM_IPSUM_WORDS)
        if rich:
            fmt = random.choices(format_choices, format_weights)[0]
            word = fmt.format(word)
        word_list.append(word)

    output = "lorem ipsum dolor " if start_with_lorem else ""
    output += " ".join(word_list) + "."
    output = output[0].upper() + output[1:]
    return output
