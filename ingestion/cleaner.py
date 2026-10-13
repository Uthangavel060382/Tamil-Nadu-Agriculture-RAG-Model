#Clean extracted text
import re


def clean_text(text):

    text = text.replace("\xa0", " ")

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()