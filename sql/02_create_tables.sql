CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    invoice_number VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('sale', 'purchase')),
    client_supplier VARCHAR(255) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    total_amount DECIMAL(15,2) NOT NULL,
    document_date DATE NOT NULL,
    due_date DATE,
    xml_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, invoice_number, type)
);