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

