-- Insert test user
INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at)
VALUES (
    '12345678-1234-1234-1234-123456789012',
    'test@test.example',
    crypt('password123', gen_salt('bf')),
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Insert sample invoices
INSERT INTO invoices (user_id, invoice_number, type, client_supplier, total_amount, document_date) VALUES
('12345678-1234-1234-1234-123456789012', '2024-001', 'sale', 'ABC Company Ltd', 1250.50, '2024-01-15'),
('12345678-1234-1234-1234-123456789012', '2024-002', 'purchase', 'XYZ Supplier Inc', 850.75, '2024-01-20');