import json


REQUIRED_KEYS = [
    "drop_id",
    "n_columns",
    "n_rows",
    "cell_width",
    "cell_height",
    "left_label_width",
    "top_header_height",
    "cells",
]


def load_metadata(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for key in REQUIRED_KEYS:
        if key not in data:
            raise ValueError(f"Champ manquant dans metadata.json : {key}")

    if not isinstance(data["cells"], list):
        raise ValueError("Le champ 'cells' doit être une liste.")

    # Without this the error only surfaces later, as a TypeError deep in the click
    # handler, on a board that looked like it had loaded fine.
    for key in ("n_columns", "n_rows", "cell_width", "cell_height",
                "left_label_width", "top_header_height"):
        value = data[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(
                f"Champ invalide dans metadata.json : {key} = {value!r} "
                "(entier positif attendu)"
            )

    if data["cell_width"] == 0 or data["cell_height"] == 0:
        raise ValueError("metadata.json : cell_width et cell_height doivent être > 0.")

    return data


def build_cell_index(cells):
    """Index cells by (row, col).

    Duplicates are a malformed board, not a valid case: keeping the last one
    silently would make a click land on metadata that belongs to another frame.
    """
    index = {}
    for cell in cells:
        key = (cell["row"], cell["col"])
        if key in index:
            raise ValueError(
                f"metadata.json : deux cellules portent row={key[0]}, col={key[1]}"
            )
        index[key] = cell
    return index
