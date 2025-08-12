
-- Drop tables in correct order (foreign keys first)
DROP TABLE IF EXISTS public.user_data CASCADE;
DROP TABLE IF EXISTS public.fatture_emesse CASCADE;
DROP TABLE IF EXISTS public.fatture_ricevute CASCADE;
DROP TABLE IF EXISTS public.payment_terms_ricevute CASCADE;
DROP TABLE IF EXISTS public.payment_terms_emesse CASCADE;
DROP TABLE IF EXISTS public.rate_fatture_emesse CASCADE;
DROP TABLE IF EXISTS public.rate_fatture_ricevute CASCADE;


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
  -- name and iban cassa are relevant for Fatture Emesse
  -- AND for Fatture Ricevute. Only for fatture emesse will
  -- be present in the invoice though.
  fe_nome_cassa varchar,
  fe_iban_cassa varchar,
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
UNIQUE (fe_partita_iva_prestatore, fe_numero_fattura, fe_data_documento);

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
    fr_nome_cassa varchar,
    fr_iban_cassa varchar,
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
UNIQUE (fr_partita_iva_prestatore, fr_numero_fattura, fr_data_documento);

CREATE TABLE public.rate_fatture_emesse (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  rfe_numero_fattura varchar NOT NULL,
    -- rfe_data_scadenza_pagamento is the old and confusing data_scadenza_rata
  rfe_data_scadenza_pagamento date NOT NULL,
  rfe_importo_pagamento_rata numeric(10,2) NOT NULL, -- CHECK (importo_pagamento_rata > 0),
  -- is casse nullable?
  rfe_nome_cassa varchar,
  rfe_iban_cassa varchar,
  rfe_notes text,
--  rfe_is_paid boolean DEFAULT false,
-- is_paid can be derived by checking the field rfe_data_pagamento_rata for null
  rfe_data_pagamento_rata date,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT rfe_pkey PRIMARY KEY (id)
  -- CONSTRAINT rfe_numero_fattura_fkey FOREIGN KEY (rfe_numero_fattura) REFERENCES fatture_emesse(fe_numero_fattura)
  -- todo: there is no unique constraint matching given keys for referenced table "fatture_emesse"
  -- i.e. the fkey must be unique in the refereced table
  );

ALTER TABLE public.rate_fatture_emesse ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage only their own data" ON public.rate_fatture_emesse
FOR ALL USING (auth.uid() = user_id);

CREATE TABLE public.rate_fatture_ricevute (
 id uuid NOT NULL DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL,
 rfr_numero_fattura varchar NOT NULL,
 rfr_data_scadenza_pagamento date NOT NULL,
 rfr_importo_pagamento_rata numeric(10,2) NOT NULL, -- CHECK (importo_pagamento_rata > 0),
-- Here, casse will have to be inputted by hand, since is the cassa from which I pay the
-- fattura ricevuta.

    -- is cassa nullable?
 rfr_nome_cassa varchar,
 rfr_iban_cassa varchar,
 rfr_notes text,
 rfr_data_pagamento_rata date,
 created_at timestamp with time zone DEFAULT now(),
 updated_at timestamp with time zone DEFAULT now(),
 CONSTRAINT rfr_pkey PRIMARY KEY (id)
 -- CONSTRAINT rfr_numero_fattura_fkey FOREIGN KEY (rfr_numero_fattura) REFERENCES fatture_ricevute(fr_numero_fattura)
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



-- Function to manage the insertion of both invoices and
-- terms in a single transactions, since Postgres functions
-- are wrapped in a single transaction by default.
--
-- The idea here is that I don't have to specify either
-- column names or values, using the incoming data structure
-- to parse the filed's name and values.
--
-- Note that for now, I'm ignoring the fact that I'm returning
-- the record id in the result.
CREATE OR REPLACE FUNCTION insert_record_fixed(
    table_name TEXT,
    record_data JSONB,
    terms_table_name TEXT DEFAULT NULL,
    terms_data JSONB[] DEFAULT NULL,
    test_user_id TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    -- We no longer need these variables since jsonb_populate_record handles the mapping
    -- columns_list TEXT;
    -- placeholders_list TEXT;
    -- values_array TEXT[];
    sql_query TEXT;
    record_id UUID;
    current_user_id UUID;
    cleaned_data JSONB := '{}'::JSONB;
    -- We no longer need these for the loop since jsonb_populate_record does the work
    key TEXT;
    value JSONB;
    insertable_columns TEXT;
    -- counter INTEGER := 1;
    term JSONB;
    -- We no longer need result_record since we can use INTO directly
    -- result_record RECORD;
BEGIN
    -- This is for testing the function without an authenticated user.
    IF test_user_id IS NULL THEN
    -- Get authenticated user ID
        current_user_id := auth.uid();
    ELSE
        current_user_id := test_user_id::UUID; -- casting from TEXT to avoid errors.
    END IF;

    -- Just to be sure, double checking that the user is logged in.
    IF current_user_id IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'User not authenticated - auth.uid() returned NULL'
        );
    END IF;

    -- Force add/override user_id (remove existing first, then add).
    -- Note that the - and || operators have not the meaning of SQL syntax,
    -- but of JSONB management.
    --
    -- - 'id' - 'created_at' - 'updated_at': because these are autogenerated with
    -- functions or triggers, I have to remove them from the list of fields inserted
    -- in the table, otherwise I get errors.
--     record_data := (record_data - 'user_id' - 'id' - 'created_at' - 'updated_at') || jsonb_build_object('user_id', current_user_id);

    -- Debug: Log what we're about to insert
    -- RAISE NOTICE 'About to insert: %', record_data;
    -- RAISE NOTICE 'User ID: %', current_user_id;

    -- Instead of building dynamic column lists and values manually,
    -- we use jsonb_populate_record which automatically maps JSONB keys to table columns.
    -- This replaces the entire loop that was building:
    -- columns_list = 'numero, cliente, importo'
    -- placeholders_list = '$1, $2, $3'
    -- values_array = ['2024-001', 'ABC Corp', '1500.50']
    --
    -- jsonb_populate_record(NULL::table_name, record_data) creates a record
    -- with the structure of table_name, populated with values from record_data
    --
    -- The old approach was:
    -- sql_query = 'INSERT INTO fatture_emesse (numero, cliente, importo) VALUES ($1, $2, $3) RETURNING id'
    -- EXECUTE sql_query USING VARIADIC values_array
    --
    -- The new approach is much simpler:
--     sql_query := format('
--         INSERT INTO %I
--         SELECT * FROM jsonb_populate_record(NULL::%I, $1)
--         RETURNING id', table_name, table_name);

--     sql_query := format('
--         INSERT INTO %I
--         SELECT * FROM jsonb_populate_record(NULL::%I, $1)', table_name, table_name);


    -- We no longer need the complex loop for building columns/values:
    -- FOR key, value IN SELECT * FROM jsonb_each(record_data) LOOP
    --     -- Skip NULL values (but keep empty strings).
    --     IF value = 'null'::JSONB THEN
    --         CONTINUE;
    --     END IF;
    --     -- Add comma if not first
    --     IF columns_list != '' THEN
    --         columns_list := columns_list || ', ';
    --         placeholders_list := placeholders_list || ', ';
    --     END IF;
    --     columns_list := columns_list || quote_ident(key);
    --     placeholders_list := placeholders_list || '$' || counter;
    --     values_array := values_array || ARRAY[value #>> '{}'];
    --     counter := counter + 1;
    -- END LOOP;

    -- Debug: Log the simplified SQL
    -- RAISE NOTICE 'SQL: %', sql_query;
    -- RAISE NOTICE 'Record data: %', record_data;

    -- Execute the simplified query - no more VARIADIC issues!
    -- The old problematic line was:
    -- EXECUTE sql_query USING VARIADIC values_array INTO record_id;
    -- The new simple line is:
--     EXECUTE sql_query USING record_data INTO record_id;






-- Clean data: remove nulls and auto-generated fields
FOR key, value IN SELECT * FROM jsonb_each(record_data)
    LOOP
    IF key NOT IN ('id', 'created_at', 'updated_at', 'user_id') AND value != 'null'::JSONB THEN
            cleaned_data := cleaned_data || jsonb_build_object(key, value);
END IF;
END LOOP;

    cleaned_data := cleaned_data || jsonb_build_object('user_id', current_user_id);

    -- Get only the columns we're actually providing data for
                 -- using j.key because, if not,  'column reference "key" is ambiguous',
SELECT string_agg(quote_ident(j.key), ', ' ORDER BY j.key) INTO insertable_columns
FROM jsonb_each_text(cleaned_data) j;

-- Build INSERT that only specifies the columns we have data for
sql_query := format('
        INSERT INTO %I (%s)
        SELECT %s FROM jsonb_populate_record(NULL::%I, $1)
        RETURNING id',
        table_name,
        insertable_columns,
        insertable_columns,
        table_name
    );

EXECUTE sql_query USING cleaned_data INTO record_id;





-- Handle terms.
    IF terms_table_name IS NOT NULL AND terms_data IS NOT NULL AND array_length(terms_data, 1) > 0 THEN
        FOR i IN 1..array_length(terms_data, 1) LOOP
            term := terms_data[i];

            term := (term - 'user_id' - 'id' - 'created_at' - 'updated_at') ||
                   jsonb_build_object('user_id', current_user_id);

            PERFORM insert_record_fixed(terms_table_name, term, NULL, NULL, test_user_id);
        END LOOP;
    END IF;

-- RETURN jsonb_build_object(
--         'success', true,
--         'id', record_id,
--         'table', table_name,
--         'user_id', current_user_id,
--         'terms_count', COALESCE(array_length(terms_data, 1), 0)
--        );

RETURN jsonb_build_object(
        'success', true,
    -- only available in except blocks
--         'error', SQLERRM,
--         'error_detail', SQLSTATE,
        'table_name', table_name,
        'original_record_data', record_data,
        'current_user_id', current_user_id,
        'test_user_id', test_user_id,
        'sql_query', sql_query
       );

EXCEPTION WHEN OTHERS THEN
--     RETURN jsonb_build_object(
--         'success', false,
--         'error', SQLERRM,
--         'error_detail', SQLSTATE,
--         'sql_query', sql_query
--     );

RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', SQLSTATE,
        'table_name', table_name,
        'original_record_data', record_data,
        'current_user_id', current_user_id,
        'test_user_id', test_user_id,
        'sql_query', sql_query
       );
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;
