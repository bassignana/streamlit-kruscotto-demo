CREATE TABLE public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email character varying NOT NULL UNIQUE,
  password_hash character varying NOT NULL,
  full_name character varying NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  last_login timestamp with time zone,
  is_active boolean DEFAULT true,
  CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE public.user_data (
                                  id uuid NOT NULL DEFAULT gen_random_uuid(),
                                  user_id uuid,
                                  data jsonb NOT NULL,
                                  created_at timestamp with time zone DEFAULT now(),
                                  updated_at timestamp with time zone DEFAULT now(),
                                  CONSTRAINT user_data_pkey PRIMARY KEY (id),
                                  CONSTRAINT user_data_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE public.fatture_emesse (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  id_codice varchar NOT NULL,
  invoice_number varchar NOT NULL,
  document_date date NOT NULL,
  total_amount numeric NOT NULL,
  due_date date,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT fatture_emesse_pkey PRIMARY KEY (id),
  CONSTRAINT fatture_emesse_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Keep id as simple primary key for DB reasons, use separate unique constraints for business rules.
ALTER TABLE public.fatture_emesse
ADD CONSTRAINT unique_composite_key
UNIQUE (id_codice, invoice_number, document_date);

CREATE TABLE public.fatture_ricevute (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    id_codice varchar NOT NULL,
    invoice_number varchar NOT NULL,
    document_date date NOT NULL,
    total_amount numeric NOT NULL,
    due_date date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT fatture_ricevute_pkey PRIMARY KEY (id),
    CONSTRAINT fatture_ricevute_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Keep id as simple primary key for DB reasons, use separate unique constraints for business rules.
ALTER TABLE public.fatture_ricevute
ADD CONSTRAINT unique_composite_key
UNIQUE (id_codice, invoice_number, document_date);

CREATE TABLE public.payment_terms (
                                      id uuid NOT NULL DEFAULT gen_random_uuid(),
                                      user_id uuid NOT NULL,
                                      invoice_id uuid NOT NULL,
                                      due_date date NOT NULL,
                                      amount numeric(10,2) NOT NULL CHECK (amount > 0),
                                      payment_method varchar NOT NULL,
                                      cash_account varchar NOT NULL,
                                      notes text,
                                      is_paid boolean DEFAULT false,
                                      payment_date date,
                                      created_at timestamp with time zone DEFAULT now(),
                                      updated_at timestamp with time zone DEFAULT now(),
                                      CONSTRAINT payment_terms_pkey PRIMARY KEY (id),
                                      CONSTRAINT payment_terms_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Add indexes for better performance
-- CREATE INDEX idx_payment_terms_user_id ON public.payment_terms(user_id);
-- CREATE INDEX idx_payment_terms_invoice_id ON public.payment_terms(invoice_id);
-- CREATE INDEX idx_payment_terms_due_date ON public.payment_terms(due_date);
-- CREATE INDEX idx_payment_terms_is_paid ON public.payment_terms(is_paid);

-- -- Add RLS (Row Level Security) policies
-- ALTER TABLE public.payment_terms ENABLE ROW LEVEL SECURITY;
--
-- -- Policy: Users can only see their own payment terms
-- CREATE POLICY "Users can view own payment terms" ON public.payment_terms
--     FOR SELECT USING (auth.uid()::text = user_id::text);
--
-- -- Policy: Users can insert their own payment terms
-- CREATE POLICY "Users can insert own payment terms" ON public.payment_terms
--     FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);
--
-- -- Policy: Users can update their own payment terms
-- CREATE POLICY "Users can update own payment terms" ON public.payment_terms
--     FOR UPDATE USING (auth.uid()::text = user_id::text);
--
-- -- Policy: Users can delete their own payment terms
-- CREATE POLICY "Users can delete own payment terms" ON public.payment_terms
--     FOR DELETE USING (auth.uid()::text = user_id::text);


-- With the following functions and triggers,
-- when I create or update a record, the created_at
-- and updated_at fields are valued AUTOMATICALLY!!!!

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_payment_terms_updated_at
    BEFORE UPDATE ON public.payment_terms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_terms_updated_at
    BEFORE UPDATE ON public.fatture_emesse
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_terms_updated_at
    BEFORE UPDATE ON public.fatture_ricevute
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create a function specifically for setting created_at on INSERT
CREATE OR REPLACE FUNCTION set_created_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at = now();
RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for INSERT operations
CREATE TRIGGER set_payment_terms_created_at
    BEFORE INSERT ON public.payment_terms
    FOR EACH ROW
    EXECUTE FUNCTION set_created_at_column();

CREATE TRIGGER set_payment_terms_created_at
    BEFORE INSERT ON public.fatture_emesse
    FOR EACH ROW
    EXECUTE FUNCTION set_created_at_column();

CREATE TRIGGER set_payment_terms_created_at
    BEFORE INSERT ON public.fatture_ricevute
    FOR EACH ROW
    EXECUTE FUNCTION set_created_at_column();