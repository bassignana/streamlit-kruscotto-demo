-- USER_ID_PLACEHOLDER will be replaced by Python script

-- Insert sample invoices using the test user ID
INSERT INTO invoices (user_id, numero_fattura, type, client_supplier, importo_totale_documento, data_documento, data_scadenza_pagamento) VALUES
('USER_ID_PLACEHOLDER', '2024-001', 'sale', 'ABC Company Ltd', 1250.50, '2024-01-15', '2024-02-15'),
('USER_ID_PLACEHOLDER', '2024-002', 'purchase', 'XYZ Supplier Inc', 850.75, '2024-01-20', '2024-02-20'),
('USER_ID_PLACEHOLDER', '2024-003', 'sale', 'DEF Corporation', 2100.00, '2024-01-25', '2024-02-25'),
('USER_ID_PLACEHOLDER', '2024-004', 'purchase', 'GHI Services', 450.25, '2024-01-30', '2024-03-01'),
('USER_ID_PLACEHOLDER', '2024-005', 'sale', 'JKL Enterprises', 3200.75, '2024-02-05', '2024-03-05');

-- Insert some sample user data
INSERT INTO user_data (user_id, data) VALUES
('USER_ID_PLACEHOLDER', '{"preferences": {"currency": "EUR", "date_format": "DD/MM/YYYY"}}'),
('USER_ID_PLACEHOLDER', '{"settings": {"notifications": true, "theme": "light"}}');