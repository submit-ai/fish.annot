def compute_cell(x_value, y_value, meta, scale=1.0):
    if scale <= 0:
        return None

    x_image = x_value / scale
    y_image = y_value / scale

    x_data = x_image - meta["left_label_width"]
    y_data = y_image - meta["top_header_height"]

    if x_data < 0 or y_data < 0:
        return None

    col = int(x_data // meta["cell_width"])
    row = int(y_data // meta["cell_height"])

    if col < 0 or col >= meta["n_columns"]:
        return None

    if row < 0 or row >= meta["n_rows"]:
        return None

    x_in_cell = x_data - (col * meta["cell_width"])
    y_in_cell = y_data - (row * meta["cell_height"])

    return {
        "row": row,
        "col": col,
        "x_image": x_image,
        "y_image": y_image,
        "x_data": x_data,
        "y_data": y_data,
        "x_in_cell": x_in_cell,
        "y_in_cell": y_in_cell,
    }