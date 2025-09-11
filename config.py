uppercase_prefixes = ['Fe ', 'Fr ', 'Rfe ', 'Rfr ', 'Ma ', 'Mp ', 'Rma ', 'Rmp ', 'C ', 'V ']
assert all([' ' in prefix for prefix in uppercase_prefixes]), 'Uppercase prefixes must end with a space.'
technical_fields = ['Id', 'User Id', 'Created At', 'Updated At']

# Since in their infinite intelligence they decided that for selecting a value
# from the dropdown menu I need to pass its index, instead of the value itself(!),
# I need to set here the options so that I can compare them.
#
# Also, since I want to avoid creating movements with Null as the value due to some errors
# that might occour, but without touching the tables for now, keep the Altro option first.
ma_tipo_options = ['Altro', 'Ordini', 'Iva']
mp_tipo_options = ['Altro', 'Iva', 'Salari e Stipendi (netti)', 'Contributi Previdenziali', 'Contributi Fiscali']
