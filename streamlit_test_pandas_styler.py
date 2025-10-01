import streamlit as st
import pandas as pd
import numpy as np

# Example DataFrame with 20 columns and 10 rows
# np.random.seed(42)  # for reproducibility
# df = pd.DataFrame(
#     np.random.randint(-10, 20, size=(10, 20)),
#     columns=[f"Col{i}" for i in range(1, 21)]
# )
#
# # CSS to style the table
# table_styles = [
#     dict(selector="th", props=[("font-size", "0.8em")]),
#     dict(selector="td", props=[("font-size", "0.8em"), ("text-align", "right")]),
#     dict(selector="tr:hover", props=[("background-color", "yellow")])
# ]
#
# # Create styled DataFrame
# styled_df = (
#     df.style
#     .apply(lambda row: ["color: red" if v < 0 else None for v in row], axis=1)  # negative numbers red
#     .set_table_styles(table_styles)  # apply CSS
# )
#
# # Render in Streamlit
# st.markdown(styled_df.to_html(), unsafe_allow_html=True)

#########################################################################
#
# # Example DataFrame with 20 columns and 10 rows
# np.random.seed(42)
# data = np.random.randint(-10, 20, size=(10, 20))
#
# # Define a MultiIndex for columns:
# #   Top level = groups ("Group 1", "Group 2", ...)
# #   Second level = actual column names ("Col1", "Col2", ...)
# top_headers = []
# sub_headers = []
#
# for i in range(1, 21):
#     group = f"Group {((i-1)//5)+1}"   # 5 columns per group
#     top_headers.append(group)
#     sub_headers.append(f"Col{i}")
#
# multi_columns = pd.MultiIndex.from_arrays([top_headers, sub_headers])
# df = pd.DataFrame(data, columns=multi_columns)
#
# # CSS to style the table
# table_styles = [
#     dict(selector="th", props=[("font-size", "0.8em")]),
#     dict(selector="td", props=[("font-size", "0.8em"), ("text-align", "right")]),
#     dict(selector="tr:hover", props=[("background-color", "yellow")])
# ]
#
# # Create styled DataFrame
# styled_df = (
#     df.style
#     .apply(lambda row: ["color: red" if v < 0 else None for v in row], axis=1)  # negative numbers red
#     .set_table_styles(table_styles)  # apply CSS
# )
#
# # Render in Streamlit
# st.markdown(styled_df.to_html(), unsafe_allow_html=True)

#####################################################################

# import streamlit as st
# import pandas as pd
# import numpy as np
#
# # Example DataFrame with 20 columns and 10 rows
# np.random.seed(42)
# data = np.random.randint(-10000, 20000, size=(10, 20)) / 100  # force decimals
#
# # MultiIndex columns: 4 groups × 5 columns
# top_headers = []
# sub_headers = []
# for i in range(1, 21):
#     group = f"Group {((i-1)//5)+1}"   # 5 columns per group
#     top_headers.append(group)
#     sub_headers.append(f"Col{i}")
#
# multi_columns = pd.MultiIndex.from_arrays([top_headers, sub_headers])
# df = pd.DataFrame(data, columns=multi_columns)
#
# # CSS to style the table (no hover highlight)
# table_styles = [
#     dict(selector="th", props=[("font-size", "0.8em")]),
#     dict(selector="td", props=[("font-size", "0.8em"), ("text-align", "right")]),
# ]
#
# # Create styled DataFrame
# styled_df = (
#     df.style
#     .apply(lambda row: ["color: red" if v < 0 else None for v in row], axis=1)  # negative numbers red
#     .set_table_styles(table_styles)
#     .format("{:,.2f}")  # formatting with thousands separator & 2 decimals
# )
#
# # Render in Streamlit
# st.markdown(styled_df.to_html(), unsafe_allow_html=True)

#####################################################################

# import streamlit as st
# import pandas as pd
# import numpy as np
#
# # Example DataFrame with 20 columns and 10 rows
# np.random.seed(42)
# data = np.random.randint(-10000, 20000, size=(10, 20)) / 100  # force decimals
#
# # MultiIndex columns: 4 groups × 5 columns
# top_headers = []
# sub_headers = []
# for i in range(1, 21):
#     group = f"Group {((i-1)//5)+1}"   # 5 columns per group
#     top_headers.append(group)
#     sub_headers.append(f"Col{i}")
#
# multi_columns = pd.MultiIndex.from_arrays([top_headers, sub_headers])
# df = pd.DataFrame(data, columns=multi_columns)
#
# # CSS to style the table (no hover highlight)
# table_styles = [
#     dict(selector="th", props=[("font-size", "0.8em")]),
#     dict(selector="td", props=[("font-size", "0.8em"), ("text-align", "right")]),
# ]
#
# # Create styled DataFrame
# styled_df = (
#     df.style
#     .apply(lambda row: ["color: red" if v < 0 else None for v in row], axis=1)  # negative numbers red
#     .set_table_styles(table_styles)
#     .format("{:,.2f}")  # formatting with thousands separator & 2 decimals
# )
#
# # Wrap in a scrollable div
# scrollable_html = f"""
# <div style="overflow-x: auto; overflow-y: auto; max-height: 500px; max-width: 100%;">
#     {styled_df.to_html()}
# </div>
# """
#
# # Render in Streamlit
# st.markdown(scrollable_html, unsafe_allow_html=True)

#####################################################################
#
# import streamlit as st
# import pandas as pd
# import numpy as np
#
# # Example DataFrame with 20 columns and 10 rows
# np.random.seed(42)
# data = np.random.randint(-10000, 20000, size=(10, 20)) / 100  # force decimals
#
# # MultiIndex columns: 4 groups × 5 columns
# top_headers = []
# sub_headers = []
# for i in range(1, 21):
#     group = f"Group {((i-1)//5)+1}"   # 5 columns per group
#     top_headers.append(group)
#     sub_headers.append(f"Col{i}")
#
# multi_columns = pd.MultiIndex.from_arrays([top_headers, sub_headers])
# df = pd.DataFrame(data, columns=multi_columns)
#
# # Add an index column for demonstration
# df.index = [f"Row {i}" for i in range(1, len(df) + 1)]
#
# # CSS to style the table (no hover highlight)
# table_styles = [
#     dict(selector="th", props=[("font-size", "0.8em")]),
#     dict(selector="td", props=[("font-size", "0.8em"), ("text-align", "right")]),
# ]
#
# # Create styled DataFrame
# styled_df = (
#     df.style
#     .apply(lambda row: ["color: red" if v < 0 else None for v in row], axis=1)  # negative numbers red
#     .set_table_styles(table_styles)
#     .format("{:,.2f}")  # formatting with thousands separator & 2 decimals
# )
#
# # Extra CSS for sticky first column
# sticky_css = """
# <style>
#     th:first-child, td:first-child {
#         position: sticky;
#         left: 0;
#         background-color: white; /* background so text isn’t overlapped */
#         z-index: 1;
#     }
# </style>
# """
#
# # Wrap in a scrollable div
# scrollable_html = f"""
# <div style="overflow-x: auto; overflow-y: auto; max-height: 500px; max-width: 100%;">
#     {styled_df.to_html()}
# </div>
# """
#
# # Render in Streamlit
# st.markdown(sticky_css + scrollable_html, unsafe_allow_html=True)

#########################################################################

# import streamlit as st
# import pandas as pd
# import numpy as np
#
# # Example DataFrame with 20 columns and 10 rows
# np.random.seed(42)
# data = np.random.randint(-10000, 20000, size=(10, 20)) / 100  # force decimals
#
# # MultiIndex columns: 4 groups × 5 columns
# top_headers = []
# sub_headers = []
# for i in range(1, 21):
#     group = f"Group {((i-1)//5)+1}"   # 5 columns per group
#     top_headers.append(group)
#     sub_headers.append(f"Col{i}")
#
# multi_columns = pd.MultiIndex.from_arrays([top_headers, sub_headers])
# df = pd.DataFrame(data, columns=multi_columns)
#
# # Add an index column for demonstration
# df.index = [f"Row {i}" for i in range(1, len(df) + 1)]
#
# # CSS to style the table
# table_styles = [
#     dict(selector="th", props=[("font-size", "0.8em")]),
#     dict(selector="td", props=[("font-size", "0.8em"), ("text-align", "right")]),
# ]
#
# # Create styled DataFrame
# styled_df = (
#     df.style
#     .apply(lambda row: ["color: red" if v < 0 else None for v in row], axis=1)  # negative numbers red
#     .set_table_styles(table_styles)
#     .format("{:,.2f}")  # formatting with thousands separator & 2 decimals
# )
#
# # CSS for sticky first + last 4 columns
# sticky_css = """
# <style>
#     /* Sticky first column */
#     th:first-child, td:first-child {
#         position: sticky;
#         left: 0;
#         background-color: white;
#         z-index: 2;
#     }
#
#     /* Sticky last 4 columns */
#     th:nth-last-child(-n+4), td:nth-last-child(-n+4) {
#         position: sticky;
#         right: 0;
#         background-color: white;
#         z-index: 1;
#     }
# </style>
# """
#
# # Wrap in a scrollable div
# scrollable_html = f"""
# <div style="overflow-x: auto; overflow-y: auto; max-height: 500px; max-width: 100%;">
#     {styled_df.to_html()}
# </div>
# """
#
# # Render in Streamlit
# st.markdown(sticky_css + scrollable_html, unsafe_allow_html=True)

#############################################################################

import streamlit as st
import pandas as pd
import numpy as np

# Example DataFrame with 20 columns and 10 rows
np.random.seed(42)
data = np.random.randint(-10000, 20000, size=(10, 20)) / 100  # force decimals

# MultiIndex columns: 4 groups × 5 columns
top_headers = []
sub_headers = []
for i in range(1, 21):
    group = f"Group {((i-1)//5)+1}"   # 5 columns per group
    top_headers.append(group)
    sub_headers.append(f"Col{i}")

multi_columns = pd.MultiIndex.from_arrays([top_headers, sub_headers])
df = pd.DataFrame(data, columns=multi_columns)

# Add an index column for demonstration
df.index = [f"Row {i}" for i in range(1, len(df) + 1)]

# CSS to style the table
table_styles = [
    dict(selector="th", props=[("font-size", "0.8em")]),
    dict(selector="td", props=[("font-size", "0.8em"), ("text-align", "right")]),
]

# Create styled DataFrame
styled_df = (
    df.style
    .apply(lambda row: ["color: red" if v < 0 else None for v in row], axis=1)  # negative numbers red
    .set_table_styles(table_styles)
    .format("{:,.2f}")  # formatting with thousands separator & 2 decimals
)

# CSS for sticky headers, first col, and last 4 cols
sticky_css = """
<style>
    /* Sticky headers (both rows in MultiIndex) */
    th {
        position: sticky;
        top: 0;
        background-color: #f9f9f9;
        z-index: 3; /* on top of other cells */
    }

    /* Sticky first column */
    th:first-child, td:first-child {
        position: sticky;
        left: 0;
        background-color: white;
        z-index: 4; /* higher so index is always visible */
    }

    /* Sticky last 4 columns */
    th:nth-last-child(-n+4), td:nth-last-child(-n+4) {
        position: sticky;
        right: 0;
        background-color: white;
        z-index: 2;
    }
</style>
"""

# Wrap in a scrollable div
scrollable_html = f"""
<div style="overflow-x: auto; overflow-y: auto; max-height: 500px; max-width: 100%;">
    {styled_df.to_html()}
</div>
"""

# Render in Streamlit
st.markdown(sticky_css + scrollable_html, unsafe_allow_html=True)
