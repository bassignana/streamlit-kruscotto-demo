
-- Drop tables in correct order (foreign keys first)
DROP TABLE IF EXISTS public.user_data CASCADE;
DROP TABLE IF EXISTS public.fatture_emesse CASCADE;
DROP TABLE IF EXISTS public.fatture_ricevute CASCADE;
DROP TABLE IF EXISTS public.payment_terms_ricevute CASCADE;
DROP TABLE IF EXISTS public.payment_terms_emesse CASCADE;
DROP TABLE IF EXISTS public.rate_fatture_emesse CASCADE;
DROP TABLE IF EXISTS public.rate_fatture_ricevute CASCADE;
DROP TABLE IF EXISTS public.movimenti_attivi CASCADE;
DROP TABLE IF EXISTS public.rate_movimenti_attivi CASCADE;
DROP TABLE IF EXISTS public.movimenti_passivi CASCADE;
DROP TABLE IF EXISTS public.rate_movimenti_passivi CASCADE;



-- 1. Nomi inglesi per campi comuni di sistema, italiani per campi unici alle tabelle
-- 2. nomi univoci che iniziano con le lettere prima degli underscore delle tabelle,
--    in modo da poter fare un search and replace in caso di cambio nome, o aggiunta.
-- ? Rompo il sistema di config XML? No, tranne se seleziono un campo sql, che dovra' essere
--   declinato con il prefisso corretto in ogni operazione
-- ? Ha senso separare nomi come id, created_at ecc? tutta la tabella deve avere il prefisso,
--   perche' quando faccio le viste avro' a che fare con campi ti tabelle diverse ma con nome uguale?
--   Forse no, perche' nelle viste posso specificare il nome della tabella,

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
  fe_partita_iva_committente varchar,
  fe_codice_fiscale_committente varchar,
  fe_nome_committente varchar,
  fe_cognome_committente varchar,
  fe_denominazione_committente varchar,
  -- Now that every type of term is managed in the rate_fatture_* table,
  -- the fe_data_scadenza_pagamento field is not needed here anymore.
  -- fe_data_scadenza_pagamento date,

  -- Due to pop operation in invoice_record_creation.py,
  -- I don't insert cassa info here but in the rate_* table.
  --   fe_nome_cassa varchar,
  --   fe_iban_cassa varchar,
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

-- Business logic:
-- I want that any term, even if the invoice has just one term,
-- to be set into the rate_fatture_* table.
-- This is so that I can verify very easily the state of an invoice,
-- regardless of its type.
CREATE TABLE public.rate_fatture_emesse (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    -- these fields are what will be used to find invoices from fatture_* table
    rfe_partita_iva_prestatore varchar NOT NULL,
    rfe_numero_fattura varchar NOT NULL,
    rfe_data_documento date NOT NULL,

    -- rfe_data_scadenza_pagamento is the old and confusing data_scadenza_rata
    rfe_data_scadenza_pagamento date NOT NULL,
    rfe_importo_pagamento_rata numeric(10,2) NOT NULL, -- CHECK (importo_pagamento_rata > 0),

    -- name and iban cassa are relevant for Fatture Emesse
    -- AND for Fatture Ricevute. Only for fatture emesse will
    -- be present in the invoice though.
    rfe_nome_cassa varchar,
    rfe_iban_cassa varchar,
    rfe_notes text,
    -- is_paid can be derived by checking the field rfe_data_pagamento_rata for null
    -- rfe_is_paid boolean DEFAULT false,
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













CREATE TABLE public.fatture_ricevute (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    fr_partita_iva_prestatore varchar NOT NULL,
    fr_numero_fattura varchar NOT NULL,
    fr_data_documento date NOT NULL,
    fr_importo_totale_documento numeric NOT NULL,
    fr_denominazione_prestatore varchar,
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


CREATE TABLE public.rate_fatture_ricevute (
 id uuid NOT NULL DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL,
 rfr_partita_iva_prestatore varchar NOT NULL,
 rfr_numero_fattura varchar NOT NULL,
 rfr_data_documento date NOT NULL,

 rfr_data_scadenza_pagamento date NOT NULL,
 rfr_importo_pagamento_rata numeric NOT NULL, -- CHECK (importo_pagamento_rata > 0),
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







CREATE TABLE public.movimenti_attivi (
                                         id uuid NOT NULL DEFAULT gen_random_uuid(),
                                         user_id uuid NOT NULL,
                                         ma_numero varchar NOT NULL,
                                         ma_data date NOT NULL,
                                         ma_importo_totale numeric NOT NULL,
                                         ma_tipo varchar,
                                         ma_cliente varchar,
                                         created_at timestamp with time zone DEFAULT now(),
                                         updated_at timestamp with time zone DEFAULT now(),
                                         CONSTRAINT movimenti_attivi_pkey PRIMARY KEY (id)
);

ALTER TABLE public.movimenti_attivi ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage only their own data" ON public.movimenti_attivi
FOR ALL USING (auth.uid() = user_id);

ALTER TABLE public.movimenti_attivi
    ADD CONSTRAINT movimenti_attivi_unique_composite_key
--         Don't know if it is good to keep ma_data in the unique key.
        UNIQUE (ma_numero, ma_data);

CREATE TABLE public.rate_movimenti_attivi (
                                              id uuid NOT NULL DEFAULT gen_random_uuid(),
                                              user_id uuid NOT NULL,
                                              rma_numero varchar NOT NULL,
                                              rma_data date NOT NULL,
                                              rma_data_scadenza date NOT NULL,
                                              rma_data_pagamento date,
                                              rma_importo_pagamento numeric NOT NULL,
                                              rma_nome_cassa varchar,
                                              rma_iban_cassa varchar,
                                              rma_notes text,
                                              created_at timestamp with time zone DEFAULT now(),
                                              updated_at timestamp with time zone DEFAULT now(),
                                              CONSTRAINT rma_pkey PRIMARY KEY (id)
);

CREATE POLICY "Users can manage only their own data" ON public.rate_movimenti_attivi
FOR ALL USING (auth.uid() = user_id);

CREATE TABLE public.movimenti_passivi (
                                         id uuid NOT NULL DEFAULT gen_random_uuid(),
                                         user_id uuid NOT NULL,
                                         mp_numero varchar NOT NULL,
                                         mp_data date NOT NULL,
                                         mp_importo_totale numeric NOT NULL,
                                         mp_tipo varchar,
                                         mp_fornitore varchar,
                                         created_at timestamp with time zone DEFAULT now(),
                                         updated_at timestamp with time zone DEFAULT now(),
                                         CONSTRAINT movimenti_passivi_pkey PRIMARY KEY (id)
);

ALTER TABLE public.movimenti_passivi ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage only their own data" ON public.movimenti_passivi
FOR ALL USING (auth.uid() = user_id);

ALTER TABLE public.movimenti_passivi
    ADD CONSTRAINT movimenti_passivi_unique_composite_key
        UNIQUE (mp_numero, mp_data);

CREATE TABLE public.rate_movimenti_passivi (
                                              id uuid NOT NULL DEFAULT gen_random_uuid(),
                                              user_id uuid NOT NULL,
                                              rmp_numero varchar NOT NULL,
                                              rmp_data date NOT NULL,
                                              rmp_data_scadenza date NOT NULL,
                                              rmp_data_pagamento date,
                                              rmp_importo_pagamento numeric NOT NULL,
                                              rmp_nome_cassa varchar,
                                              rmp_iban_cassa varchar,
                                              rmp_notes text,
                                              created_at timestamp with time zone DEFAULT now(),
                                              updated_at timestamp with time zone DEFAULT now(),
                                              CONSTRAINT rmp_pkey PRIMARY KEY (id)
);

CREATE POLICY "Users can manage only their own data" ON public.rate_movimenti_passivi
FOR ALL USING (auth.uid() = user_id);

-- Add indexes for better performance
-- CREATE INDEX idx_payment_terms_user_id ON public.payment_terms(user_id);
-- CREATE INDEX idx_payment_terms_invoice_id ON public.payment_terms(invoice_id);
-- CREATE INDEX idx_payment_terms_data_scadenza_pagamento ON public.payment_terms(data_scadenza_pagamento);
-- CREATE INDEX idx_payment_terms_is_paid ON public.payment_terms(is_paid);


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

CREATE TRIGGER update_payment_terms_updated_at
    BEFORE UPDATE ON public.movimenti_attivi
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_terms_updated_at
    BEFORE UPDATE ON public.rate_movimenti_attivi
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_terms_updated_at
    BEFORE UPDATE ON public.movimenti_passivi
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_terms_updated_at
    BEFORE UPDATE ON public.rate_movimenti_passivi
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

CREATE TRIGGER set_payment_terms_created_at
    BEFORE INSERT ON public.movimenti_attivi
    FOR EACH ROW
    EXECUTE FUNCTION set_created_at_column();

CREATE TRIGGER set_payment_terms_created_at
    BEFORE INSERT ON public.rate_movimenti_attivi
    FOR EACH ROW
    EXECUTE FUNCTION set_created_at_column();

CREATE TRIGGER set_payment_terms_created_at
    BEFORE INSERT ON public.movimenti_passivi
    FOR EACH ROW
    EXECUTE FUNCTION set_created_at_column();

CREATE TRIGGER set_payment_terms_created_at
    BEFORE INSERT ON public.rate_movimenti_passivi
    FOR EACH ROW
    EXECUTE FUNCTION set_created_at_column();



-- Function to manage the insertion of both invoices and
-- terms in a single transactions, since Postgres functions
-- are wrapped in a single transaction by default.
--
-- The idea here is that I don't have to specify either
-- column names or values, using the input data structure
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






-- FATTURE EMESSE CASH FLOW
CREATE OR REPLACE VIEW cashflow_next_12_months AS
WITH date_calculations AS (
    SELECT
        CURRENT_DATE AS today,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day' AS current_month_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months' - INTERVAL '1 day' AS next_month_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '3 months' - INTERVAL '1 day' AS month_plus_2_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '4 months' - INTERVAL '1 day' AS month_plus_3_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '5 months' - INTERVAL '1 day' AS month_plus_4_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '6 months' - INTERVAL '1 day' AS month_plus_5_end
),
unpaid_invoices AS (
    SELECT
        rfe.*,
        dc.today,
        dc.current_month_end,
        dc.next_month_end,
        dc.month_plus_2_end,
        dc.month_plus_3_end,
        dc.month_plus_4_end,
        dc.month_plus_5_end,
        -- Calculate days difference for aging
        rfe_data_scadenza_pagamento - dc.today AS days_to_due,
        -- Determine if overdue
        CASE
            WHEN rfe_data_scadenza_pagamento < dc.today THEN TRUE
            ELSE FALSE
        END AS is_overdue,
        -- Calculate overdue days (negative means future due date)
        dc.today - rfe_data_scadenza_pagamento AS overdue_days
    FROM rate_fatture_emesse rfe
    CROSS JOIN date_calculations dc
    WHERE
        -- Only include unpaid invoices TODO; does this constraint make sense?
        rfe_data_pagamento_rata IS NULL
        -- Exclude invoices paid in previous months
        AND NOT (rfe_data_pagamento_rata IS NOT NULL
                AND rfe_data_pagamento_rata < DATE_TRUNC('month', dc.today))
)
SELECT
    -- Future collections (incassare_*)
    ROUND(COALESCE(SUM(
                           CASE
                               WHEN NOT is_overdue AND rfe_data_scadenza_pagamento <= current_month_end
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS incassare_30gg,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > current_month_end
                                   AND rfe_data_scadenza_pagamento <= next_month_end
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS incassare_60gg,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > next_month_end
                                   AND rfe_data_scadenza_pagamento <= month_plus_2_end
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS incassare_90gg,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > month_plus_2_end
                                   AND rfe_data_scadenza_pagamento <= month_plus_3_end
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS incassare_120gg,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > month_plus_3_end
                                   AND rfe_data_scadenza_pagamento <= month_plus_4_end
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS incassare_150gg,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > month_plus_4_end
                                   AND rfe_data_scadenza_pagamento <= month_plus_5_end
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS incassare_180gg,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > month_plus_5_end
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS incassare_oltre,

    -- Overdue collections (scaduti_*)
    ROUND(COALESCE(SUM(
                           CASE
                               WHEN is_overdue AND overdue_days <= 30
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS scaduti_30gg,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN is_overdue AND overdue_days > 30 AND overdue_days <= 60
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS scaduti_60gg,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN is_overdue AND overdue_days > 60 AND overdue_days <= 90
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS scaduti_90gg,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN is_overdue AND overdue_days > 90
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS scaduti_oltre,

    -- Summary totals
    ROUND(COALESCE(SUM(
                           CASE
                               WHEN NOT is_overdue
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS totale_da_incassare,

    ROUND(COALESCE(SUM(
                           CASE
                               WHEN is_overdue
                                   THEN rfe_importo_pagamento_rata
                               ELSE 0
                               END
                   ), 0)::numeric, 2) AS totale_scaduti,

    ROUND(COALESCE(SUM(rfe_importo_pagamento_rata), 0)::numeric, 2) AS totale_generale,

    -- Additional useful information
    COUNT(*) AS numero_rate_totali,
    COUNT(CASE WHEN is_overdue THEN 1 END) AS numero_rate_scadute,
    COUNT(CASE WHEN NOT is_overdue THEN 1 END) AS numero_rate_future,

    -- Reference date for the calculation
    MAX(today) AS data_calcolo

FROM unpaid_invoices;




-- FATTURE EMESSE CASH FLOW GROUP BY CASSE
-- Cashflow View for next 12 months grouped by bank accounts
-- CREATE OR REPLACE VIEW cashflow_next_12_months_groupby AS
-- WITH date_calc AS (
--     SELECT
--         CURRENT_DATE AS today,
--         DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day' AS m1_end,
--         DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months' - INTERVAL '1 day' AS m2_end,
--         DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '3 months' - INTERVAL '1 day' AS m3_end,
--         DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '4 months' - INTERVAL '1 day' AS m4_end,
--         DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '5 months' - INTERVAL '1 day' AS m5_end,
--         DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '6 months' - INTERVAL '1 day' AS m6_end
-- ),
-- unpaid AS (
--     SELECT
--         rfe.*,
--         dc.*,
--         rfe_data_scadenza_pagamento < dc.today AS is_overdue,
--         dc.today - rfe_data_scadenza_pagamento AS overdue_days,
--         COALESCE(NULLIF(TRIM(rfe_nome_cassa), ''), NULLIF(TRIM(rfe_iban_cassa), ''), 'Non specificato') AS cassa
--     FROM rate_fatture_emesse rfe
--     CROSS JOIN date_calc dc
--     WHERE rfe_data_pagamento_rata IS NULL
-- ),
-- cassa_data AS (
--     SELECT
--         cassa,
--         CASE
--             WHEN cassa = 'Non specificato' THEN '2_'
--             ELSE '1_'
--         END || cassa AS sort_key,
--
--         -- Future collections
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento <= m1_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_30gg,
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m1_end AND rfe_data_scadenza_pagamento <= m2_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_60gg,
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m2_end AND rfe_data_scadenza_pagamento <= m3_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_90gg,
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m3_end AND rfe_data_scadenza_pagamento <= m4_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_120gg,
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m4_end AND rfe_data_scadenza_pagamento <= m5_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_150gg,
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m5_end AND rfe_data_scadenza_pagamento <= m6_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_180gg,
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m6_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_oltre,
--
--         -- Overdue collections
--         ROUND(SUM(CASE WHEN is_overdue AND overdue_days <= 30 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_30gg,
--         ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 30 AND overdue_days <= 60 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_60gg,
--         ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 60 AND overdue_days <= 90 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_90gg,
--         ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 90 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_oltre,
--
--         -- Totals
--         ROUND(SUM(CASE WHEN NOT is_overdue THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS totale_da_incassare,
--         ROUND(SUM(CASE WHEN is_overdue THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS totale_scaduti,
--         ROUND(SUM(rfe_importo_pagamento_rata)::numeric, 2) AS totale_generale,
--
--         COUNT(*) AS numero_rate_totali,
--         COUNT(CASE WHEN is_overdue THEN 1 END) AS numero_rate_scadute,
--         MAX(today) AS data_calcolo
--     FROM unpaid
--     GROUP BY cassa
--
--     UNION ALL
--
--     -- Totals row
--     SELECT
--         'Totali' AS cassa,
--         '3_Totali' AS sort_key,
--
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento <= m1_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m1_end AND rfe_data_scadenza_pagamento <= m2_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m2_end AND rfe_data_scadenza_pagamento <= m3_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m3_end AND rfe_data_scadenza_pagamento <= m4_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m4_end AND rfe_data_scadenza_pagamento <= m5_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m5_end AND rfe_data_scadenza_pagamento <= m6_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m6_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--
--         ROUND(SUM(CASE WHEN is_overdue AND overdue_days <= 30 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 30 AND overdue_days <= 60 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 60 AND overdue_days <= 90 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 90 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--
--         ROUND(SUM(CASE WHEN NOT is_overdue THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(CASE WHEN is_overdue THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
--         ROUND(SUM(rfe_importo_pagamento_rata)::numeric, 2),
--
--         COUNT(*),
--         COUNT(CASE WHEN is_overdue THEN 1 END),
--         MAX(today)
--     FROM unpaid
-- )
-- SELECT
--     cassa,
--     incassare_30gg, incassare_60gg, incassare_90gg, incassare_120gg, incassare_150gg, incassare_180gg, incassare_oltre,
--     scaduti_30gg, scaduti_60gg, scaduti_90gg, scaduti_oltre,
--     totale_da_incassare, totale_scaduti, totale_generale,
--     numero_rate_totali, numero_rate_scadute, data_calcolo
-- FROM cassa_data
-- ORDER BY sort_key;


-- MAIN DASHBOARD CASHFLOW
-- GROUP BY CASSE - COMBINES rate_fatture_emesse AND rate_movimenti_attivi
DROP VIEW IF EXISTS active_cashflow_next_12_months_groupby_casse;
CREATE VIEW active_cashflow_next_12_months_groupby_casse AS
WITH date_calc AS (
    SELECT
                CURRENT_DATE AS today,
                DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day' AS m1_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months' - INTERVAL '1 day' AS m2_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '3 months' - INTERVAL '1 day' AS m3_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '4 months' - INTERVAL '1 day' AS m4_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '5 months' - INTERVAL '1 day' AS m5_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '6 months' - INTERVAL '1 day' AS m6_end
        ),
-- Combine both sources into unified structure
        unpaid AS (
    -- Data from rate_fatture_emesse
        SELECT
        rfe_data_scadenza_pagamento,
        rfe_importo_pagamento_rata,
        rfe_nome_cassa,
        rfe_iban_cassa,
        dc.*,
        rfe_data_scadenza_pagamento < dc.today AS is_overdue,
        dc.today - rfe_data_scadenza_pagamento AS overdue_days,
        COALESCE(NULLIF(TRIM(rfe_nome_cassa), ''), NULLIF(TRIM(rfe_iban_cassa), ''), 'Non specificato') AS cassa
        FROM rate_fatture_emesse rfe
        CROSS JOIN date_calc dc
        WHERE rfe_data_pagamento_rata IS NULL

        UNION ALL

    -- Data from rate_movimenti_attivi
        SELECT
        rma_data_scadenza AS rfe_data_scadenza_pagamento,
        rma_importo_pagamento AS rfe_importo_pagamento_rata,
        rma_nome_cassa AS rfe_nome_cassa,
        rma_iban_cassa AS rfe_iban_cassa,
        dc.*,
        rma_data_scadenza < dc.today AS is_overdue,
        dc.today - rma_data_scadenza AS overdue_days,
        COALESCE(NULLIF(TRIM(rma_nome_cassa), ''), NULLIF(TRIM(rma_iban_cassa), ''), 'Non specificato') AS cassa
        FROM rate_movimenti_attivi rma
        CROSS JOIN date_calc dc
        WHERE rma_data_pagamento IS NULL
        ),
        cassa_data AS (
        SELECT
        cassa,
        CASE
        WHEN cassa = 'Non specificato' THEN '2_'
        ELSE '1_'
        END || cassa AS sort_key,

    -- Future collections
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento <= m1_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_30gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m1_end AND rfe_data_scadenza_pagamento <= m2_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_60gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m2_end AND rfe_data_scadenza_pagamento <= m3_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_90gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m3_end AND rfe_data_scadenza_pagamento <= m4_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_120gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m4_end AND rfe_data_scadenza_pagamento <= m5_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_150gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m5_end AND rfe_data_scadenza_pagamento <= m6_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_180gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m6_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS incassare_oltre,

    -- Overdue collections
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days <= 30 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_30gg,
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 30 AND overdue_days <= 60 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_60gg,
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 60 AND overdue_days <= 90 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_90gg,
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 90 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_oltre,

    -- Totals
        ROUND(SUM(CASE WHEN NOT is_overdue THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS totale_da_incassare,
        ROUND(SUM(CASE WHEN is_overdue THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS totale_scaduti,
        ROUND(SUM(rfe_importo_pagamento_rata)::numeric, 2) AS totale_generale
        FROM unpaid
        GROUP BY cassa

        UNION ALL

    -- Totals row
        SELECT
        'Totali' AS cassa,
        '3_Totali' AS sort_key,

        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento <= m1_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m1_end AND rfe_data_scadenza_pagamento <= m2_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m2_end AND rfe_data_scadenza_pagamento <= m3_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m3_end AND rfe_data_scadenza_pagamento <= m4_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m4_end AND rfe_data_scadenza_pagamento <= m5_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m5_end AND rfe_data_scadenza_pagamento <= m6_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfe_data_scadenza_pagamento > m6_end THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),

        ROUND(SUM(CASE WHEN is_overdue AND overdue_days <= 30 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 30 AND overdue_days <= 60 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 60 AND overdue_days <= 90 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 90 THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),

        ROUND(SUM(CASE WHEN NOT is_overdue THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN is_overdue THEN rfe_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(rfe_importo_pagamento_rata)::numeric, 2)
        FROM unpaid
        )
SELECT
    cassa,
    incassare_30gg, incassare_60gg, incassare_90gg, incassare_120gg, incassare_150gg, incassare_180gg, incassare_oltre,
    scaduti_30gg, scaduti_60gg, scaduti_90gg, scaduti_oltre,
    totale_da_incassare, totale_scaduti, totale_generale
FROM cassa_data
ORDER BY sort_key;


-- PAYABLES DASHBOARD CASHFLOW
-- GROUP BY CASSE - COMBINES rate_fatture_ricevute AND rate_movimenti_passivi
DROP VIEW IF EXISTS passive_cashflow_next_12_months_groupby_casse;
CREATE VIEW passive_cashflow_next_12_months_groupby_casse AS
WITH date_calc AS (
    SELECT
                CURRENT_DATE AS today,
                DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day' AS m1_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months' - INTERVAL '1 day' AS m2_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '3 months' - INTERVAL '1 day' AS m3_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '4 months' - INTERVAL '1 day' AS m4_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '5 months' - INTERVAL '1 day' AS m5_end,
        DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '6 months' - INTERVAL '1 day' AS m6_end
        ),
-- Combine both sources into unified structure
        unpaid AS (
    -- Data from rate_fatture_ricevute
        SELECT
        rfr_data_scadenza_pagamento,
        rfr_importo_pagamento_rata,
        rfr_nome_cassa,
        rfr_iban_cassa,
        dc.*,
        rfr_data_scadenza_pagamento < dc.today AS is_overdue,
        dc.today - rfr_data_scadenza_pagamento AS overdue_days,
        COALESCE(NULLIF(TRIM(rfr_nome_cassa), ''), NULLIF(TRIM(rfr_iban_cassa), ''), 'Non specificato') AS cassa
        FROM rate_fatture_ricevute rfr
        CROSS JOIN date_calc dc
        WHERE rfr_data_pagamento_rata IS NULL

        UNION ALL

    -- Data from rate_movimenti_passivi
        SELECT
        rmp_data_scadenza AS rfr_data_scadenza_pagamento,
        rmp_importo_pagamento AS rfr_importo_pagamento_rata,
        rmp_nome_cassa AS rfr_nome_cassa,
        rmp_iban_cassa AS rfr_iban_cassa,
        dc.*,
        rmp_data_scadenza < dc.today AS is_overdue,
        dc.today - rmp_data_scadenza AS overdue_days,
        COALESCE(NULLIF(TRIM(rmp_nome_cassa), ''), NULLIF(TRIM(rmp_iban_cassa), ''), 'Non specificato') AS cassa
        FROM rate_movimenti_passivi rmp
        CROSS JOIN date_calc dc
        WHERE rmp_data_pagamento IS NULL
        ),
        cassa_data AS (
        SELECT
        cassa,
        CASE
        WHEN cassa = 'Non specificato' THEN '2_'
        ELSE '1_'
        END || cassa AS sort_key,

    -- Future payments
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento <= m1_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS pagare_30gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m1_end AND rfr_data_scadenza_pagamento <= m2_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS pagare_60gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m2_end AND rfr_data_scadenza_pagamento <= m3_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS pagare_90gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m3_end AND rfr_data_scadenza_pagamento <= m4_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS pagare_120gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m4_end AND rfr_data_scadenza_pagamento <= m5_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS pagare_150gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m5_end AND rfr_data_scadenza_pagamento <= m6_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS pagare_180gg,
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m6_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS pagare_oltre,

    -- Overdue payments
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days <= 30 THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_30gg,
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 30 AND overdue_days <= 60 THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_60gg,
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 60 AND overdue_days <= 90 THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_90gg,
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 90 THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS scaduti_oltre,

    -- Totals
        ROUND(SUM(CASE WHEN NOT is_overdue THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS totale_da_pagare,
        ROUND(SUM(CASE WHEN is_overdue THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2) AS totale_scaduti,
        ROUND(SUM(rfr_importo_pagamento_rata)::numeric, 2) AS totale_generale
        FROM unpaid
        GROUP BY cassa

        UNION ALL

    -- Totals row
        SELECT
        'Totali' AS cassa,
        '3_Totali' AS sort_key,

        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento <= m1_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m1_end AND rfr_data_scadenza_pagamento <= m2_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m2_end AND rfr_data_scadenza_pagamento <= m3_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m3_end AND rfr_data_scadenza_pagamento <= m4_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m4_end AND rfr_data_scadenza_pagamento <= m5_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m5_end AND rfr_data_scadenza_pagamento <= m6_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN NOT is_overdue AND rfr_data_scadenza_pagamento > m6_end THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),

        ROUND(SUM(CASE WHEN is_overdue AND overdue_days <= 30 THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 30 AND overdue_days <= 60 THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 60 AND overdue_days <= 90 THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN is_overdue AND overdue_days > 90 THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),

        ROUND(SUM(CASE WHEN NOT is_overdue THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(CASE WHEN is_overdue THEN rfr_importo_pagamento_rata ELSE 0 END)::numeric, 2),
        ROUND(SUM(rfr_importo_pagamento_rata)::numeric, 2)
        FROM unpaid
        )
SELECT
    cassa,
    pagare_30gg, pagare_60gg, pagare_90gg, pagare_120gg, pagare_150gg, pagare_180gg, pagare_oltre,
    scaduti_30gg, scaduti_60gg, scaduti_90gg, scaduti_oltre,
    totale_da_pagare, totale_scaduti, totale_generale
FROM cassa_data
ORDER BY sort_key;

-- FATTURE EMESSE MAIN DASHBOARD
-- Invoice Payment Summary View
-- Shows invoice details with payment status from both tables
CREATE OR REPLACE VIEW invoice_payment_summary AS
WITH payment_aggregates AS (
    SELECT
        rfe_partita_iva_prestatore,
        rfe_numero_fattura,
        rfe_data_documento,

        -- Total amount already paid (where payment date is not null)
        ROUND(COALESCE(SUM(
            CASE
                WHEN rfe_data_pagamento_rata IS NOT NULL
                THEN rfe_importo_pagamento_rata
                ELSE 0
            END
        ), 0)::numeric, 2) AS totale_incassato,

        -- Total amount still unpaid (where payment date is null)
        ROUND(COALESCE(SUM(
            CASE
                WHEN rfe_data_pagamento_rata IS NULL
                THEN rfe_importo_pagamento_rata
                ELSE 0
            END
        ), 0)::numeric, 2) AS totale_saldo,

        -- Latest payment date for this invoice
        MAX(rfe_data_pagamento_rata) AS ultima_data_pagamento

    FROM rate_fatture_emesse
    GROUP BY rfe_partita_iva_prestatore, rfe_numero_fattura, rfe_data_documento
)
SELECT
    -- Use payment date if available, otherwise use document date
    COALESCE(pa.ultima_data_pagamento, fe.fe_data_documento) AS data,

    fe.fe_numero_fattura AS numero,

    -- Build client name: prioritize nome+cognome, fallback to denominazione
    CASE
        WHEN fe.fe_nome_committente IS NOT NULL AND TRIM(fe.fe_nome_committente) != ''
        THEN TRIM(fe.fe_nome_committente) ||
             CASE
                 WHEN fe.fe_cognome_committente IS NOT NULL AND TRIM(fe.fe_cognome_committente) != ''
                 THEN ' ' || TRIM(fe.fe_cognome_committente)
                 ELSE ''
                 END
        WHEN fe.fe_denominazione_committente IS NOT NULL AND TRIM(fe.fe_denominazione_committente) != ''
        THEN TRIM(fe.fe_denominazione_committente)
        ELSE 'Cliente non specificato'
        END AS cliente,

    ROUND(fe.fe_importo_totale_documento::numeric, 2) AS totale,

    COALESCE(pa.totale_incassato, 0.00) AS incassato,

    COALESCE(pa.totale_saldo, 0.00) AS saldo,

    -- Additional useful fields
    fe.fe_data_documento AS data_fattura,
    pa.ultima_data_pagamento AS data_ultimo_pagamento,

    -- Payment status indicator
    CASE
        WHEN pa.totale_saldo = 0 OR pa.totale_saldo IS NULL THEN 'Completamente Pagata'
        WHEN pa.totale_incassato = 0 OR pa.totale_incassato IS NULL THEN 'Non Pagata'
        ELSE 'Parzialmente Pagata'
        END AS stato_pagamento,

    -- Percentage paid
    CASE
        WHEN fe.fe_importo_totale_documento > 0
            THEN ROUND((COALESCE(pa.totale_incassato, 0) / fe.fe_importo_totale_documento * 100)::numeric, 1)
        ELSE 0
        END AS percentuale_incassata

FROM fatture_emesse fe
         LEFT JOIN payment_aggregates pa ON (
    fe.fe_partita_iva_prestatore = pa.rfe_partita_iva_prestatore
        AND fe.fe_numero_fattura = pa.rfe_numero_fattura
        AND fe.fe_data_documento = pa.rfe_data_documento
    )
ORDER BY
    COALESCE(pa.ultima_data_pagamento, fe.fe_data_documento) DESC,
    fe.fe_numero_fattura;





-- EMESSE SIMPLE DASHBOARD
CREATE OR REPLACE VIEW fatture_emesse_overview AS
WITH payment_aggregates AS (
    SELECT
        rfe_partita_iva_prestatore,
        rfe_numero_fattura,
        rfe_data_documento,

        -- IPORTANT BUSINESS CONSTRAINTS TO VERIFY:
        -- Total amount already paid (where payment date is not null)
        ROUND(COALESCE(SUM(
            CASE
                WHEN rfe_data_pagamento_rata IS NOT NULL
                THEN rfe_importo_pagamento_rata
                ELSE 0
            END
        ), 0)::numeric, 2) AS totale_incassato,

        -- Total amount still unpaid (where payment date is null)
        ROUND(COALESCE(SUM(
            CASE
                WHEN rfe_data_pagamento_rata IS NULL
                THEN rfe_importo_pagamento_rata
                ELSE 0
            END
        ), 0)::numeric, 2) AS totale_saldo,

        -- Latest payment date for this invoice
        MAX(rfe_data_pagamento_rata) AS ultima_data_pagamento

    FROM rate_fatture_emesse
    GROUP BY rfe_partita_iva_prestatore, rfe_numero_fattura, rfe_data_documento
)
SELECT
    -- IPORTANT BUSINESS CONSTRAINTS TO VERIFY:
    -- Use payment date if available, otherwise use document date
    COALESCE(pa.ultima_data_pagamento, fe.fe_data_documento) AS data,

    fe.fe_numero_fattura AS numero,

    -- Build client name: prioritize nome+cognome, fallback to denominazione
    CASE
        WHEN fe.fe_nome_committente IS NOT NULL AND TRIM(fe.fe_nome_committente) != ''
        THEN TRIM(fe.fe_nome_committente) ||
             CASE
                 WHEN fe.fe_cognome_committente IS NOT NULL AND TRIM(fe.fe_cognome_committente) != ''
                 THEN ' ' || TRIM(fe.fe_cognome_committente)
                 ELSE ''
                 END
        WHEN fe.fe_denominazione_committente IS NOT NULL AND TRIM(fe.fe_denominazione_committente) != ''
        THEN TRIM(fe.fe_denominazione_committente)
        ELSE 'Cliente non specificato'
        END AS cliente,

    ROUND(fe.fe_importo_totale_documento::numeric, 2) AS totale,

    COALESCE(pa.totale_incassato, 0.00) AS incassato,

    COALESCE(pa.totale_saldo, 0.00) AS saldo,

    -- Additional useful fields
    fe.fe_data_documento AS data_fattura,
    pa.ultima_data_pagamento AS data_ultimo_pagamento,

    -- Payment status indicator
    CASE
        WHEN pa.totale_saldo = 0 OR pa.totale_saldo IS NULL THEN 'Completamente Pagata'
        WHEN pa.totale_incassato = 0 OR pa.totale_incassato IS NULL THEN 'Non Pagata'
        ELSE 'Parzialmente Pagata'
        END AS stato_pagamento,

    -- Percentage paid
    CASE
        WHEN fe.fe_importo_totale_documento > 0
            THEN ROUND((COALESCE(pa.totale_incassato, 0) / fe.fe_importo_totale_documento * 100)::numeric, 1)
        ELSE 0
        END AS percentuale_incassata

FROM fatture_emesse fe
         LEFT JOIN payment_aggregates pa ON (
    fe.fe_partita_iva_prestatore = pa.rfe_partita_iva_prestatore
        AND fe.fe_numero_fattura = pa.rfe_numero_fattura
        AND fe.fe_data_documento = pa.rfe_data_documento
    )
ORDER BY
    COALESCE(pa.ultima_data_pagamento, fe.fe_data_documento) DESC,
    fe.fe_numero_fattura;



-- RICEVUTE SIMPLE DASHBOARD
CREATE OR REPLACE VIEW fatture_ricevute_overview AS
WITH payment_aggregates AS (
    SELECT
        rfr_partita_iva_prestatore,
        rfr_numero_fattura,
        rfr_data_documento,

        -- IPORTANT BUSINESS CONSTRAINTS TO VERIFY:
        -- Total amount already paid (where payment date is not null)
        ROUND(COALESCE(SUM(
            CASE
                WHEN rfr_data_pagamento_rata IS NOT NULL
                THEN rfr_importo_pagamento_rata
                ELSE 0
            END
        ), 0)::numeric, 2) AS totale_incassato,

        -- Total amount still unpaid (where payment date is null)
        ROUND(COALESCE(SUM(
            CASE
                WHEN rfr_data_pagamento_rata IS NULL
                THEN rfr_importo_pagamento_rata
                ELSE 0
            END
        ), 0)::numeric, 2) AS totale_saldo,

        -- Latest payment date for this invoice
        MAX(rfr_data_pagamento_rata) AS ultima_data_pagamento

    FROM rate_fatture_ricevute
    GROUP BY rfr_partita_iva_prestatore, rfr_numero_fattura, rfr_data_documento
)
SELECT
    -- IPORTANT BUSINESS CONSTRAINTS TO VERIFY:
    -- Use payment date if available, otherwise use document date
    COALESCE(pa.ultima_data_pagamento, fr.fr_data_documento) AS data,

    fr.fr_numero_fattura AS numero,

    -- Build client name: prioritize nome+cognome, fallback to denominazione
    CASE
        WHEN fr.fr_denominazione_prestatore IS NOT NULL AND TRIM(fr.fr_denominazione_prestatore) != ''
        THEN TRIM(fr.fr_denominazione_prestatore)
        ELSE 'Prestatore non specificato'
        END AS cliente,

    ROUND(fr.fr_importo_totale_documento::numeric, 2) AS totale,

    COALESCE(pa.totale_incassato, 0.00) AS incassato,

    COALESCE(pa.totale_saldo, 0.00) AS saldo,

    -- Additional useful fields
    fr.fr_data_documento AS data_fattura,
    pa.ultima_data_pagamento AS data_ultimo_pagamento,

    -- Payment status indicator
    CASE
        WHEN pa.totale_saldo = 0 OR pa.totale_saldo IS NULL THEN 'Completamente Pagata'
        WHEN pa.totale_incassato = 0 OR pa.totale_incassato IS NULL THEN 'Non Pagata'
        ELSE 'Parzialmente Pagata'
        END AS stato_pagamento,

    -- Percentage paid
    CASE
        WHEN fr.fr_importo_totale_documento > 0
            THEN ROUND((COALESCE(pa.totale_incassato, 0) / fr.fr_importo_totale_documento * 100)::numeric, 1)
        ELSE 0
        END AS percentuale_incassata

FROM fatture_ricevute fr
         LEFT JOIN payment_aggregates pa ON (
    fr.fr_partita_iva_prestatore = pa.rfr_partita_iva_prestatore
        AND fr.fr_numero_fattura = pa.rfr_numero_fattura
        AND fr.fr_data_documento = pa.rfr_data_documento
    )
ORDER BY
    COALESCE(pa.ultima_data_pagamento, fr.fr_data_documento) DESC,
    fr.fr_numero_fattura;







-- Monthly Invoice Summary View
-- Shows monthly totals for sales invoices, purchase invoices, and balance
CREATE OR REPLACE VIEW monthly_invoice_summary AS
WITH monthly_sales AS (
    SELECT
        EXTRACT(MONTH FROM fe_data_documento) AS mese,
        ROUND(SUM(fe_importo_totale_documento)::numeric, 2) AS importo_vendite
    FROM fatture_emesse
    WHERE EXTRACT(YEAR FROM fe_data_documento) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY EXTRACT(MONTH FROM fe_data_documento)
),
monthly_purchases AS (
    SELECT
        EXTRACT(MONTH FROM fr_data_documento) AS mese,
        ROUND(SUM(fr_importo_totale_documento)::numeric, 2) AS importo_acquisti
    FROM fatture_ricevute
    WHERE EXTRACT(YEAR FROM fr_data_documento) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY EXTRACT(MONTH FROM fr_data_documento)
),
combined_data AS (
    SELECT
        COALESCE(s.mese, p.mese, m.mese) AS mese,
        COALESCE(s.importo_vendite, 0) AS vendite,
        COALESCE(p.importo_acquisti, 0) AS acquisti,
        COALESCE(s.importo_vendite, 0) - COALESCE(p.importo_acquisti, 0) AS saldo
    FROM (SELECT generate_series(1, 12) AS mese) m
    FULL OUTER JOIN monthly_sales s ON m.mese = s.mese
    FULL OUTER JOIN monthly_purchases p ON m.mese = p.mese
)
SELECT
    tipo_fattura,
    ROUND(COALESCE(gennaio, 0.00)::numeric, 2) AS gennaio,
    ROUND(COALESCE(febbraio, 0.00)::numeric, 2) AS febbraio,
    ROUND(COALESCE(marzo, 0.00)::numeric, 2) AS marzo,
    ROUND(COALESCE(aprile, 0.00)::numeric, 2) AS aprile,
    ROUND(COALESCE(maggio, 0.00)::numeric, 2) AS maggio,
    ROUND(COALESCE(giugno, 0.00)::numeric, 2) AS giugno,
    ROUND(COALESCE(luglio, 0.00)::numeric, 2) AS luglio,
    ROUND(COALESCE(agosto, 0.00)::numeric, 2) AS agosto,
    ROUND(COALESCE(settembre, 0.00)::numeric, 2) AS settembre,
    ROUND(COALESCE(ottobre, 0.00)::numeric, 2) AS ottobre,
    ROUND(COALESCE(novembre, 0.00)::numeric, 2) AS novembre,
    ROUND(COALESCE(dicembre, 0.00)::numeric, 2) AS dicembre,
    ROUND((COALESCE(gennaio, 0) + COALESCE(febbraio, 0) + COALESCE(marzo, 0) + COALESCE(aprile, 0) +
           COALESCE(maggio, 0) + COALESCE(giugno, 0) + COALESCE(luglio, 0) + COALESCE(agosto, 0) +
           COALESCE(settembre, 0) + COALESCE(ottobre, 0) + COALESCE(novembre, 0) + COALESCE(dicembre, 0))::numeric, 2) AS totale_anno
FROM (
         -- Sales invoices row
         SELECT
             'Fatture di Vendita' AS tipo_fattura,
             SUM(CASE WHEN mese = 1 THEN vendite ELSE 0 END) AS gennaio,
             SUM(CASE WHEN mese = 2 THEN vendite ELSE 0 END) AS febbraio,
             SUM(CASE WHEN mese = 3 THEN vendite ELSE 0 END) AS marzo,
             SUM(CASE WHEN mese = 4 THEN vendite ELSE 0 END) AS aprile,
             SUM(CASE WHEN mese = 5 THEN vendite ELSE 0 END) AS maggio,
             SUM(CASE WHEN mese = 6 THEN vendite ELSE 0 END) AS giugno,
             SUM(CASE WHEN mese = 7 THEN vendite ELSE 0 END) AS luglio,
             SUM(CASE WHEN mese = 8 THEN vendite ELSE 0 END) AS agosto,
             SUM(CASE WHEN mese = 9 THEN vendite ELSE 0 END) AS settembre,
             SUM(CASE WHEN mese = 10 THEN vendite ELSE 0 END) AS ottobre,
             SUM(CASE WHEN mese = 11 THEN vendite ELSE 0 END) AS novembre,
             SUM(CASE WHEN mese = 12 THEN vendite ELSE 0 END) AS dicembre,
             1 AS ordine
         FROM combined_data

         UNION ALL

         -- Purchase invoices row
         SELECT
             'Fatture di Acquisto' AS tipo_fattura,
             SUM(CASE WHEN mese = 1 THEN acquisti ELSE 0 END) AS gennaio,
             SUM(CASE WHEN mese = 2 THEN acquisti ELSE 0 END) AS febbraio,
             SUM(CASE WHEN mese = 3 THEN acquisti ELSE 0 END) AS marzo,
             SUM(CASE WHEN mese = 4 THEN acquisti ELSE 0 END) AS aprile,
             SUM(CASE WHEN mese = 5 THEN acquisti ELSE 0 END) AS maggio,
             SUM(CASE WHEN mese = 6 THEN acquisti ELSE 0 END) AS giugno,
             SUM(CASE WHEN mese = 7 THEN acquisti ELSE 0 END) AS luglio,
             SUM(CASE WHEN mese = 8 THEN acquisti ELSE 0 END) AS agosto,
             SUM(CASE WHEN mese = 9 THEN acquisti ELSE 0 END) AS settembre,
             SUM(CASE WHEN mese = 10 THEN acquisti ELSE 0 END) AS ottobre,
             SUM(CASE WHEN mese = 11 THEN acquisti ELSE 0 END) AS novembre,
             SUM(CASE WHEN mese = 12 THEN acquisti ELSE 0 END) AS dicembre,
             2 AS ordine
         FROM combined_data

         UNION ALL

         -- Balance row (Sales - Purchases)
         SELECT
             'Saldo' AS tipo_fattura,
             SUM(CASE WHEN mese = 1 THEN saldo ELSE 0 END) AS gennaio,
             SUM(CASE WHEN mese = 2 THEN saldo ELSE 0 END) AS febbraio,
             SUM(CASE WHEN mese = 3 THEN saldo ELSE 0 END) AS marzo,
             SUM(CASE WHEN mese = 4 THEN saldo ELSE 0 END) AS aprile,
             SUM(CASE WHEN mese = 5 THEN saldo ELSE 0 END) AS maggio,
             SUM(CASE WHEN mese = 6 THEN saldo ELSE 0 END) AS giugno,
             SUM(CASE WHEN mese = 7 THEN saldo ELSE 0 END) AS luglio,
             SUM(CASE WHEN mese = 8 THEN saldo ELSE 0 END) AS agosto,
             SUM(CASE WHEN mese = 9 THEN saldo ELSE 0 END) AS settembre,
             SUM(CASE WHEN mese = 10 THEN saldo ELSE 0 END) AS ottobre,
             SUM(CASE WHEN mese = 11 THEN saldo ELSE 0 END) AS novembre,
             SUM(CASE WHEN mese = 12 THEN saldo ELSE 0 END) AS dicembre,
             3 AS ordine
         FROM combined_data
     ) summary
ORDER BY ordine;


-- Monthly Movements Summary View

DROP VIEW IF EXISTS monthly_altri_movimenti_summary;
CREATE VIEW monthly_altri_movimenti_summary AS
WITH
monthly_sales AS (
    SELECT
        EXTRACT(MONTH FROM ma_data) AS mese,
        ROUND(SUM(ma_importo_totale)::numeric, 2) AS importo_vendite
    FROM movimenti_attivi
    WHERE EXTRACT(YEAR FROM ma_data) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY EXTRACT(MONTH FROM ma_data)
),
monthly_purchases AS (
    SELECT
        EXTRACT(MONTH FROM mp_data) AS mese,
        ROUND(SUM(mp_importo_totale)::numeric, 2) AS importo_acquisti
    FROM movimenti_passivi
    WHERE EXTRACT(YEAR FROM mp_data) = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY EXTRACT(MONTH FROM mp_data)
),
combined_data AS (
    SELECT
        COALESCE(s.mese, p.mese, m.mese) AS mese,
        COALESCE(s.importo_vendite, 0) AS vendite,
        COALESCE(p.importo_acquisti, 0) AS acquisti,
        COALESCE(s.importo_vendite, 0) - COALESCE(p.importo_acquisti, 0) AS saldo
    FROM (SELECT generate_series(1, 12) AS mese) m
    FULL OUTER JOIN monthly_sales s ON m.mese = s.mese
    FULL OUTER JOIN monthly_purchases p ON m.mese = p.mese
)
SELECT
    tipo_movimento,
    ROUND(COALESCE(gennaio, 0.00)::numeric, 2) AS gennaio,
    ROUND(COALESCE(febbraio, 0.00)::numeric, 2) AS febbraio,
    ROUND(COALESCE(marzo, 0.00)::numeric, 2) AS marzo,
    ROUND(COALESCE(aprile, 0.00)::numeric, 2) AS aprile,
    ROUND(COALESCE(maggio, 0.00)::numeric, 2) AS maggio,
    ROUND(COALESCE(giugno, 0.00)::numeric, 2) AS giugno,
    ROUND(COALESCE(luglio, 0.00)::numeric, 2) AS luglio,
    ROUND(COALESCE(agosto, 0.00)::numeric, 2) AS agosto,
    ROUND(COALESCE(settembre, 0.00)::numeric, 2) AS settembre,
    ROUND(COALESCE(ottobre, 0.00)::numeric, 2) AS ottobre,
    ROUND(COALESCE(novembre, 0.00)::numeric, 2) AS novembre,
    ROUND(COALESCE(dicembre, 0.00)::numeric, 2) AS dicembre
--     ROUND((COALESCE(gennaio, 0) + COALESCE(febbraio, 0) + COALESCE(marzo, 0) + COALESCE(aprile, 0) +
--            COALESCE(maggio, 0) + COALESCE(giugno, 0) + COALESCE(luglio, 0) + COALESCE(agosto, 0) +
--            COALESCE(settembre, 0) + COALESCE(ottobre, 0) + COALESCE(novembre, 0) + COALESCE(dicembre, 0))::numeric, 2) AS totale_anno
FROM (
         -- Sales invoices row
         SELECT
             'Movimenti Attivi' AS tipo_movimento,
             SUM(CASE WHEN mese = 1 THEN vendite ELSE 0 END) AS gennaio,
             SUM(CASE WHEN mese = 2 THEN vendite ELSE 0 END) AS febbraio,
             SUM(CASE WHEN mese = 3 THEN vendite ELSE 0 END) AS marzo,
             SUM(CASE WHEN mese = 4 THEN vendite ELSE 0 END) AS aprile,
             SUM(CASE WHEN mese = 5 THEN vendite ELSE 0 END) AS maggio,
             SUM(CASE WHEN mese = 6 THEN vendite ELSE 0 END) AS giugno,
             SUM(CASE WHEN mese = 7 THEN vendite ELSE 0 END) AS luglio,
             SUM(CASE WHEN mese = 8 THEN vendite ELSE 0 END) AS agosto,
             SUM(CASE WHEN mese = 9 THEN vendite ELSE 0 END) AS settembre,
             SUM(CASE WHEN mese = 10 THEN vendite ELSE 0 END) AS ottobre,
             SUM(CASE WHEN mese = 11 THEN vendite ELSE 0 END) AS novembre,
             SUM(CASE WHEN mese = 12 THEN vendite ELSE 0 END) AS dicembre,
             1 AS ordine
         FROM combined_data

         UNION ALL

         -- Purchase invoices row
         SELECT
             'Movimenti Passivi' AS tipo_movimento,
             SUM(CASE WHEN mese = 1 THEN acquisti ELSE 0 END) AS gennaio,
             SUM(CASE WHEN mese = 2 THEN acquisti ELSE 0 END) AS febbraio,
             SUM(CASE WHEN mese = 3 THEN acquisti ELSE 0 END) AS marzo,
             SUM(CASE WHEN mese = 4 THEN acquisti ELSE 0 END) AS aprile,
             SUM(CASE WHEN mese = 5 THEN acquisti ELSE 0 END) AS maggio,
             SUM(CASE WHEN mese = 6 THEN acquisti ELSE 0 END) AS giugno,
             SUM(CASE WHEN mese = 7 THEN acquisti ELSE 0 END) AS luglio,
             SUM(CASE WHEN mese = 8 THEN acquisti ELSE 0 END) AS agosto,
             SUM(CASE WHEN mese = 9 THEN acquisti ELSE 0 END) AS settembre,
             SUM(CASE WHEN mese = 10 THEN acquisti ELSE 0 END) AS ottobre,
             SUM(CASE WHEN mese = 11 THEN acquisti ELSE 0 END) AS novembre,
             SUM(CASE WHEN mese = 12 THEN acquisti ELSE 0 END) AS dicembre,
             2 AS ordine
         FROM combined_data

         UNION ALL

         -- Balance row (Sales - Purchases)
         SELECT
             'Saldo' AS tipo_movimento,
             SUM(CASE WHEN mese = 1 THEN saldo ELSE 0 END) AS gennaio,
             SUM(CASE WHEN mese = 2 THEN saldo ELSE 0 END) AS febbraio,
             SUM(CASE WHEN mese = 3 THEN saldo ELSE 0 END) AS marzo,
             SUM(CASE WHEN mese = 4 THEN saldo ELSE 0 END) AS aprile,
             SUM(CASE WHEN mese = 5 THEN saldo ELSE 0 END) AS maggio,
             SUM(CASE WHEN mese = 6 THEN saldo ELSE 0 END) AS giugno,
             SUM(CASE WHEN mese = 7 THEN saldo ELSE 0 END) AS luglio,
             SUM(CASE WHEN mese = 8 THEN saldo ELSE 0 END) AS agosto,
             SUM(CASE WHEN mese = 9 THEN saldo ELSE 0 END) AS settembre,
             SUM(CASE WHEN mese = 10 THEN saldo ELSE 0 END) AS ottobre,
             SUM(CASE WHEN mese = 11 THEN saldo ELSE 0 END) AS novembre,
             SUM(CASE WHEN mese = 12 THEN saldo ELSE 0 END) AS dicembre,
             3 AS ordine
         FROM combined_data
     ) summary
ORDER BY ordine;