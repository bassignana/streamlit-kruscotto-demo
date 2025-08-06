-- 1. Nomi inglesi per campi comuni, italiani per campi comuni
-- 2. nomi univoci che iniziano con le lettere prima degli underscore delle tabelle,
-- in modo da poter fare un search and replace in caso di cambio nome, o aggiunta.
-- ? Rompo il sistema di config XML? No, tranne se seleziono un campo sql, che dovra' essere
--   declinato con il prefisso corretto in ogni operazione
-- ? Ha senso separare nomi come id, created_at ecc? tutta la tabella deve avere il prefisso,
--   perche' quando faccio le viste avro' a che fare con campi ti tabelle diverse ma con nome uguale?
--   Forse no, perche' nelle viste posso specificare il nome della tabella,
-- 3. Testare il parsing xml con findall
-- 4. Rifare direttamente il gestore delle scadenze? sicuramente andra' rivisto
-- Prefix are composed by the first letter of the table and every letter before the underscore,
-- all in lowercase
CREATE TABLE public.user_data (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  -- codice fiscale e partita iva sono necessari per identificare l'azienda
  -- all'interno delle fatture
  ud_codice_fiscale varchar NOT NULL,
  ud_partita_iva varchar NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_data_pkey PRIMARY KEY (id)
);

ALTER TABLE public.user_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage only their own data" ON public.user_data
FOR ALL USING (auth.uid() = user_id);

CREATE TABLE public.fatture_emesse (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  fe_partita_iva_prestatore varchar NOT NULL,
  fe_numero_fattura varchar NOT NULL,
  fe_data_documento date NOT NULL,
  fe_importo_totale_documento numeric NOT NULL,
  fe_partita_iva_committente numeric,
  fe_codice_fiscale_committente varchar,
  fe_nome_committente varchar,
  fe_cognome_committente varchar,
  fe_denominazione_committente varchar,
  -- if there is one data_scadenza_pagamento, it goes in this table, otherwise
  -- all the dates and respective quantity go as 2 or more 'scadenza' in another table
  fe_data_scadenza_pagamento date,
  -- name and IBAN cassa relevant only for Fatture Emesse
  fe_nome_cassa varchar,
  fe_IBAN_cassa varchar,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT fatture_emesse_pkey PRIMARY KEY (id)
);

ALTER TABLE public.fatture_emesse ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage only their own data" ON public.fatture_emesse
FOR ALL USING (auth.uid() = user_id);

-- Keep id as simple primary key for DB reasons, use separate unique constraints for business rules.
ALTER TABLE public.fatture_emesse
ADD CONSTRAINT emesse_unique_composite_key
UNIQUE (partita_iva_prestatore, numero_fattura, data_documento);

CREATE TABLE public.fatture_ricevute (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    fr_partita_iva_prestatore varchar NOT NULL,
    fr_numero_fattura varchar NOT NULL,
    fr_data_documento date NOT NULL,
    fr_denominazione_prestatore varchar,
    fr_importo_totale_documento numeric NOT NULL,
    -- if there is one data_scadenza_pagamento, it goes in this table, otherwise
    -- all the dates and respective quantity go as 2 or more 'scadenza' in another table
    fr_data_scadenza_pagamento date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT fatture_ricevute_pkey PRIMARY KEY (id)
);

ALTER TABLE public.fatture_ricevute ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage only their own data" ON public.fatture_ricevute
FOR ALL USING (auth.uid() = user_id);

-- Keep id as simple primary key for DB reasons, use separate unique constraints for business rules.
ALTER TABLE public.fatture_ricevute
ADD CONSTRAINT ricevute_unique_composite_key
UNIQUE (partita_iva_prestatore, numero_fattura, data_documento);

CREATE TABLE public.rate_fatture_emesse (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  rfe_numero_fattura uuid NOT NULL,
  rfe_data_scadenza_rata date NOT NULL,
  rfe_importo_pagamento_rata numeric(10,2) NOT NULL CHECK (importo_pagamento_rata > 0),
  rfe_nome_cassa varchar NOT NULL,
  rfe_IBAN_cassa varchar NOT NULL,
  rfe_notes text,
--  rfe_is_paid boolean DEFAULT false,
-- is_paid can be derived by checking the field rfe_data_pagamento_rata for null
  rfe_data_pagamento_rata date,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT rfe_pkey PRIMARY KEY (id),
  CONSTRAINT rfe_numero_fattura_fkey FOREIGN KEY (rfe_numero_fattura) REFERENCES fatture_emesse(fe_numero_fattura)
);

ALTER TABLE public.rate_fatture_emesse ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage only their own data" ON public.rate_fatture_emesse
FOR ALL USING (auth.uid() = user_id);

CREATE TABLE public.rate_fatture_ricevute (
 id uuid NOT NULL DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL,
 rfr_numero_fattura uuid NOT NULL,
 rfr_data_scadenza_rata date NOT NULL,
 rfr_importo_pagamento_rata numeric(10,2) NOT NULL CHECK (importo_pagamento_rata > 0),
-- Here, casse will have to be inputted by hand, since is the cassa from which I pay the
-- fattura ricevuta.
 rfr_nome_cassa varchar NOT NULL,
 rfr_IBAN_cassa varchar NOT NULL,
 rfr_notes text,
 rfr_data_pagamento_rata date,
 created_at timestamp with time zone DEFAULT now(),
 updated_at timestamp with time zone DEFAULT now(),
 CONSTRAINT rfr_pkey PRIMARY KEY (id),
 CONSTRAINT rfr_numero_fattura_fkey FOREIGN KEY (rfr_numero_fattura) REFERENCES fatture_ricevute(fr_numero_fattura)
);

ALTER TABLE public.rate_fatture_ricevute ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage only their own data" ON public.rate_fatture_ricevute
FOR ALL USING (auth.uid() = user_id);

-- Add indexes for better performance
-- CREATE INDEX idx_payment_terms_user_id ON public.payment_terms(user_id);
-- CREATE INDEX idx_payment_terms_invoice_id ON public.payment_terms(invoice_id);
-- CREATE INDEX idx_payment_terms_data_scadenza_pagamento ON public.payment_terms(data_scadenza_pagamento);
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
    BEFORE UPDATE ON public.rate_fatture_emesse
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_terms_updated_at
    BEFORE UPDATE ON public.rate_fatture_ricevute
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
    BEFORE INSERT ON public.rate_fatture_emesse
    FOR EACH ROW
    EXECUTE FUNCTION set_created_at_column();

CREATE TRIGGER set_payment_terms_created_at
    BEFORE INSERT ON public.rate_fatture_ricevute
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