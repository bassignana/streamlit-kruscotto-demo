"""
If pandas styler does not work, I can try to use st.html()
"""
import pandas as pd
import numpy as np
import streamlit as st

df = pd.DataFrame(np.random.randn(5, 12), columns=[f"col{i+1}" for i in range(12)])
columns = pd.MultiIndex.from_tuples(
    [('test1', f'col{i+1}') if i < 9 else ('test2', f'col{i+1}') for i in range(12)]
)
df.columns = columns

# Unreproducible pandas doc example
# df = pd.DataFrame(np.random.randn(10, 4),
#                   columns=['A', 'B', 'C', 'D'])
# df.style.set_table_styles(
#     [{'selector': 'tr:hover',
#       'props': [('background-color', 'yellow')]}]
# )

st.dataframe(df)

# Get the html version of the dataframe.
# print(df.style.to_html())

#
#
# # style = df.style.set_table_styles(
# #     [{'selector': '.col_heading .level0 .col0',
# #       'props': [('background-color', 'yellow')]}]
# # )
#
# cell_hover = {  # for row hover use <tr> instead of <td>
#     'selector': 'td:hover',
#     'props': [('background-color', '#ffffb3')]
# }
# index_names = {
#     'selector': '.index_name',
#     'props': 'font-style: italic; color: darkgrey; font-weight:normal;'
# }
# headers = {
#     'selector': 'th:not(.index_name)',
#     'props': 'background-color: #000066; color: white;'
# }
# df.style.set_table_styles([cell_hover, index_names, headers])
#
# # style = df.style.set_table_styles(
# #     [{'selector': '.col_heading .level0 .col0',
# #       'props': [('background-color', 'yellow')]}]
# # )
#
# df
# st.dataframe(df)