# ui_utils.py

import streamlit as st
import pandas as pd

def get_table_height(num_rows: int, row_height: int = 35, extra_height: int = 60, max_height: int = 1000) -> int:
    """
    Calculate an appropriate height for a table component to avoid scrolling.

    Args:
        num_rows (int): Number of rows in the table.
        row_height (int): Estimated height per row in pixels.
        extra_height (int): Height buffer for headers/padding.
        max_height (int): Optional max height to cap the result.

    Returns:
        int: Total height in pixels.
    """
    height = num_rows * row_height + extra_height
    return min(height, max_height)