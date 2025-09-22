import pandas as pd
import streamlit as st
import numpy as np

columns = [
    "Cassa",
    "Settembre",
    "Ottobre",
    "Novembre",
    "Dicembre",
    "Gennaio",
    "Febbraio",
    "Marzo",
    "Aprile",
    "Maggio",
    "Giugno",
    "Luglio",
    "Agosto",
    "Incassare Oltre",
    "Scaduti 30Gg",
    "Scaduti 60Gg",
    "Scaduti Oltre",
    "Totale Attivi"
]

dummy_values = np.random.randint(1000, 5000, size=len(columns))
df = pd.DataFrame([dummy_values], columns=columns)
st.dataframe(df)

df.columns = pd.MultiIndex.from_arrays([
                                               [
                                                   'ATTIVI',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare',
                                                   'Da Incassare Scaduti',
                                                   'Da Incassare Scaduti',
                                                   'Da Incassare Scaduti',
                                                   'Totale'
                                               ],
                                            df.columns])

st.dataframe(df)

st.write("df.columns after mulitindex (the pair are tuples)")
st.write(df.columns)
