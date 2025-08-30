uppercase_prefixes = ['Fe ', 'Fr ', 'Rfe ', 'Rfr ', 'Ma ', 'Mp ', 'Rma ', 'Rmp ', 'C ']
assert all([' ' in prefix for prefix in uppercase_prefixes]), 'Uppercase prefixes must end with a space.'
technical_fields = ['Id', 'User Id', 'Created At', 'Updated At']
