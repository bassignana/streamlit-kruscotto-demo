
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
DROP TABLE IF EXISTS public.casse CASCADE;



-- 1. Nomi inglesi per campi comuni di sistema, italiani per campi unici alle tabelle
-- 2. nomi univoci che iniziano con le lettere prima degli underscore delle tabelle,
--    in modo da poter fare un search and replace in caso di cambio nome, o aggiunta.
-- ? Rompo il sistema di config XML? No, tranne se seleziono un campo sql, che dovra' essere
--   declinato con il prefisso corretto in ogni operazione
-- ? Ha senso separare nomi come id, created_at ecc? tutta la tabella deve avere il prefisso,
--   perche' quando faccio le viste avro' a che fare con campi ti tabelle diverse ma con nome uguale?
--   Forse no, perche' nelle viste posso specificare il nome della tabella,

-- Add a constraint so that I cannot insert an empty row, if there isn't a default for that.

-- This table cannot have an fkey that references rate_fatture_emesse, because it is only used,
-- for now, in combination with a view on the frontend.
CREATE TABLE public.casse (
      id uuid NOT NULL DEFAULT gen_random_uuid(),
      user_id uuid NOT NULL,
      c_nome_cassa varchar,
      c_iban_cassa varchar,
      c_descrizione_cassa varchar,
      created_at timestamp with time zone DEFAULT now(),
      updated_at timestamp with time zone DEFAULT now(),
      CONSTRAINT casse_pkey PRIMARY KEY (id)
      -- FOREIGN KEY (user_id, c_nome_cassa, c_iban_cassa) REFERENCES
      --    public.rate_fatture_emesse (user_id, rfe_nome_cassa, rfe_iban_cassa)
);

-- WHY do I have c_descrizione_cassa in the unique constraint?
ALTER TABLE public.casse
    ADD CONSTRAINT casse_composite_key
        UNIQUE (user_id, c_nome_cassa, c_iban_cassa, c_descrizione_cassa);

ALTER TABLE public.casse ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage only their own data" ON public.casse
FOR ALL USING (auth.uid() = user_id);



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
    ADD CONSTRAINT fatture_emesse_unique_index_for_rate_fkey
        UNIQUE (user_id, fe_partita_iva_prestatore, fe_numero_fattura, fe_data_documento);



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
    CONSTRAINT rfe_pkey PRIMARY KEY (id),
    FOREIGN KEY (user_id, rfe_partita_iva_prestatore, rfe_numero_fattura, rfe_data_documento)
        REFERENCES public.fatture_emesse (user_id, fe_partita_iva_prestatore, fe_numero_fattura, fe_data_documento)
            ON DELETE CASCADE ON UPDATE CASCADE
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
    ADD CONSTRAINT fatture_ricevute_unique_index_for_rate_fkey
        UNIQUE (user_id, fr_partita_iva_prestatore, fr_numero_fattura, fr_data_documento);



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
 CONSTRAINT rfr_pkey PRIMARY KEY (id),
 FOREIGN KEY (user_id, rfr_partita_iva_prestatore, rfr_numero_fattura, rfr_data_documento)
    REFERENCES public.fatture_ricevute (user_id, fr_partita_iva_prestatore, fr_numero_fattura, fr_data_documento)
       ON DELETE CASCADE ON UPDATE CASCADE

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
    ADD CONSTRAINT movimenti_attivi_unique_index_for_rate_fkey
        UNIQUE (user_id, ma_numero, ma_data);



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
                                              CONSTRAINT rma_pkey PRIMARY KEY (id),
    FOREIGN KEY (user_id, rma_numero, rma_data) REFERENCES public.movimenti_attivi (user_id, ma_numero, ma_data)
          ON DELETE CASCADE ON UPDATE CASCADE
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
    ADD CONSTRAINT movimenti_passivi_unique_index_for_rate_fkey
        UNIQUE (user_id, mp_numero, mp_data);



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
                                              CONSTRAINT rmp_pkey PRIMARY KEY (id),
  FOREIGN KEY (user_id, rmp_numero, rmp_data) REFERENCES public.movimenti_passivi (user_id, mp_numero, mp_data)
  ON DELETE CASCADE ON UPDATE CASCADE
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

CREATE TRIGGER update_payment_terms_updated_at
    BEFORE UPDATE ON public.casse
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

CREATE TRIGGER set_payment_terms_created_at
    BEFORE INSERT ON public.casse
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
    sql_query TEXT;
    record_id UUID;
    current_user_id UUID;
    cleaned_data JSONB := '{}'::JSONB;
    key TEXT;
    value JSONB;
    insertable_columns TEXT;
    term JSONB;
BEGIN
    -- This is for testing the function without an authenticated user.
    IF test_user_id IS NULL THEN
    -- Get authenticated user ID
        current_user_id := auth.uid();
    ELSE
        current_user_id := test_user_id::UUID; -- casting UUID from TEXT to avoid errors.
    END IF;

    -- Just to be sure, double check that the user is logged in.
    IF current_user_id IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'User not authenticated - auth.uid() returned NULL'
        );
    END IF;

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

    RETURN jsonb_build_object(
            'success', true,
        -- only available in except blocks
        -- 'error', SQLERRM,
        -- 'error_detail', SQLSTATE,
            'table_name', table_name,
            'original_record_data', record_data,
            'current_user_id', current_user_id,
            'test_user_id', test_user_id,
            'sql_query', sql_query
           );

    EXCEPTION WHEN OTHERS THEN

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


-- Use for testing, while impersonating.
-- SELECT upsert_terms(
--                'rate_movimenti_attivi',
--                '{"rma_numero": "2024-001", "rma_data": "2024-01-15"}',
--                ARRAY[
--                    '{"user_id": "test-user", "rma_numero": "2024-001", "rma_data": "2024-01-15", "rma_data_scadenza": "2024-02-15", "rma_importo_pagamento": 1250.50, "rma_nome_cassa": "Conto Corrente Principale", "rma_notes": "Prima rata pagamento", "created_at": "2024-01-01T10:00:00Z", "updated_at": null}'::JSONB,
--                '{"user_id": "test-user", "rma_numero": "2024-001", "rma_data": "2024-01-15", "rma_data_scadenza": "2024-03-15", "rma_importo_pagamento": 850.75, "rma_nome_cassa": "Cassa Contanti", "rma_notes": "Seconda rata pagamento", "rma_data_pagamento": "2024-03-10"}'::JSONB
-- ]
--        );
CREATE OR REPLACE FUNCTION upsert_terms(
       table_name TEXT,
       delete_key JSONB,
       terms JSONB[]
) RETURNS JSONB AS $$
DECLARE
user_id UUID;
key TEXT;
        term JSONB;
        field JSONB;
        cleaned_data JSONB[] := ARRAY[]::JSONB[];  -- This creates an empty array;
        cleaned_term JSONB;
        delete_where_clause TEXT;
        delete_query TEXT;
        insertable_columns TEXT;
        insert_query TEXT;
BEGIN
        user_id := auth.uid();


        -- Remove nulls and auto-generated fields if present.
        FOREACH term IN ARRAY terms LOOP
            cleaned_term := '{}'::JSONB;
FOR key, field IN SELECT * FROM jsonb_each(term)
                                    LOOP
    IF key NOT IN ('id', 'created_at', 'updated_at', 'user_id') AND field != 'null'::JSONB THEN
                        cleaned_term := cleaned_term || jsonb_build_object(key, field);
END IF;
END LOOP;
            cleaned_term := cleaned_term || jsonb_build_object('user_id', user_id);
            cleaned_data := array_append(cleaned_data, cleaned_term);
END LOOP;

        -- Test with:
        -- SELECT string_agg(dk.key || ' = ' || dk.value, ' AND ')
        -- FROM jsonb_each_text('{"rma_numero": "2024-001", "rma_data": "2024-01-15"}') dk;
        delete_key := delete_key || jsonb_build_object('user_id', user_id);
SELECT string_agg(dk.key || ' = ' || quote_literal(dk.value), ' AND ') INTO delete_where_clause
FROM jsonb_each_text(delete_key) dk;

delete_query := format('
            DELETE FROM %I
            WHERE %s',
            table_name,
            delete_where_clause
        );
EXECUTE delete_query;

SELECT string_agg(quote_ident(col.key), ', ' ORDER BY col.key) INTO insertable_columns
FROM jsonb_each_text(cleaned_data[1]) col;

insert_query := format('
            INSERT INTO %I (%s)
            SELECT %s FROM jsonb_populate_record(NULL::%I, $1)',
            table_name,
            insertable_columns,
            insertable_columns,
            table_name);

        IF terms IS NOT NULL AND array_length(cleaned_data, 1) > 0 THEN
        FOR i IN 1..array_length(cleaned_data, 1) LOOP
            term := cleaned_data[i];
EXECUTE insert_query USING term;
END LOOP;
END IF;

        -- RAISE EXCEPTION 'insert_query: %', insert_query;

RETURN jsonb_build_object(
        'success', true,
        'table_name', table_name,
        'original_record_data', terms
       );

EXCEPTION WHEN OTHERS THEN

        RETURN jsonb_build_object(
                'success', false,
                'error', SQLERRM,
                'error_detail', SQLSTATE,
                'cleaned_data', cleaned_data,
                'table_name', table_name,
                'original_record_data', terms
            );

END
$$ LANGUAGE plpgsql SECURITY INVOKER;




-- FATTURE EMESSE CASH FLOW
DROP VIEW IF EXISTS cashflow_next_12_months;
CREATE VIEW cashflow_next_12_months WITH (security_invoker = true) AS
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


-- MAIN DASHBOARD CASHFLOW
-- GROUP BY CASSE - COMBINES rate_fatture_emesse AND rate_movimenti_attivi
DROP VIEW IF EXISTS active_cashflow_next_12_months_groupby_casse;
CREATE VIEW active_cashflow_next_12_months_groupby_casse WITH (security_invoker = true) AS
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
CREATE VIEW passive_cashflow_next_12_months_groupby_casse WITH (security_invoker = true) AS
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
DROP VIEW IF EXISTS invoice_payment_summary;
CREATE VIEW invoice_payment_summary WITH (security_invoker = true) AS
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





DROP VIEW IF EXISTS fatture_emesse_overview;
CREATE VIEW fatture_emesse_overview WITH (security_invoker = true) AS
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
        ), 0)::numeric, 2) AS totale_saldo

    FROM rate_fatture_emesse
    WHERE user_id = auth.uid()
    GROUP BY rfe_partita_iva_prestatore, rfe_numero_fattura, rfe_data_documento
)
SELECT
    fe.id as id,
    fe.fe_data_documento AS fe_data_documento,
    fe.fe_numero_fattura AS fe_numero_fattura,

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
        END AS v_cliente,

    ROUND(fe.fe_importo_totale_documento::numeric, 2) AS fe_importo_totale_documento,
    COALESCE(pa.totale_incassato, 0.00) AS v_incassato,
    COALESCE(pa.totale_saldo, 0.00) AS v_saldo

FROM fatture_emesse fe
LEFT JOIN payment_aggregates pa ON (
    fe.fe_partita_iva_prestatore = pa.rfe_partita_iva_prestatore
        AND fe.fe_numero_fattura = pa.rfe_numero_fattura
        AND fe.fe_data_documento = pa.rfe_data_documento
    )
WHERE user_id = auth.uid()
ORDER BY
    fe.fe_data_documento DESC,
    fe.fe_numero_fattura;



DROP VIEW IF EXISTS fatture_ricevute_overview;
CREATE VIEW fatture_ricevute_overview WITH (security_invoker = true) AS
WITH payment_aggregates AS (
    SELECT
        rfr_partita_iva_prestatore,
        rfr_numero_fattura,
        rfr_data_documento,

        -- Total amount already paid (where payment date is not null)
        ROUND(COALESCE(SUM(
            CASE
                WHEN rfr_data_pagamento_rata IS NOT NULL
                THEN rfr_importo_pagamento_rata
                ELSE 0
            END
        ), 0)::numeric, 2) AS totale_pagato,

        -- Total amount still unpaid (where payment date is null)
        ROUND(COALESCE(SUM(
            CASE
                WHEN rfr_data_pagamento_rata IS NULL
                THEN rfr_importo_pagamento_rata
                ELSE 0
            END
        ), 0)::numeric, 2) AS totale_saldo

        -- Latest payment date for this invoice
        -- MAX(rfr_data_pagamento_rata) AS ultima_data_pagamento

    FROM rate_fatture_ricevute
    WHERE user_id = auth.uid()
    GROUP BY rfr_partita_iva_prestatore, rfr_numero_fattura, rfr_data_documento
)
SELECT
    fr.id as id,
    fr.fr_data_documento AS fr_data_documento,
    fr.fr_numero_fattura AS fr_numero_fattura,

    CASE
        WHEN fr.fr_denominazione_prestatore IS NOT NULL AND TRIM(fr.fr_denominazione_prestatore) != ''
        THEN TRIM(fr.fr_denominazione_prestatore)
        ELSE 'Fornitore non specificato'
        END AS v_fornitore,

    ROUND(fr.fr_importo_totale_documento::numeric, 2) AS fr_importo_totale_documento,
    COALESCE(pa.totale_pagato, 0.00) AS v_pagato,
    COALESCE(pa.totale_saldo, 0.00) AS v_saldo

FROM fatture_ricevute fr
         LEFT JOIN payment_aggregates pa ON (
    fr.fr_partita_iva_prestatore = pa.rfr_partita_iva_prestatore
        AND fr.fr_numero_fattura = pa.rfr_numero_fattura
        AND fr.fr_data_documento = pa.rfr_data_documento
    )
WHERE user_id = auth.uid()
ORDER BY
    fr.fr_data_documento DESC,
    fr.fr_numero_fattura;



DROP VIEW IF EXISTS movimenti_attivi_overview;
CREATE VIEW movimenti_attivi_overview WITH (security_invoker = true) AS
    WITH payment_aggregates AS (
    SELECT
    rma_numero,
    rma_data,

    -- Total amount already paid (where payment date is not null)
    ROUND(COALESCE(SUM(
    CASE
    WHEN rma_data_pagamento IS NOT NULL
    THEN rma_importo_pagamento
    ELSE 0
    END
), 0)::numeric, 2) AS totale_pagato,

    -- Total amount still unpaid (where payment date is null)
    ROUND(COALESCE(SUM(
    CASE
    WHEN rma_data_pagamento IS NULL
    THEN rma_importo_pagamento
    ELSE 0
    END
), 0)::numeric, 2) AS totale_saldo

    FROM rate_movimenti_attivi
    WHERE user_id = auth.uid()
    GROUP BY rma_numero, rma_data
)
SELECT
    -- I take the id so it is easier to identify records without composing their unique composite key
    ma.id as id,
    ma.ma_data AS ma_data,
    ma.ma_numero AS ma_numero,

    CASE
        WHEN ma.ma_cliente IS NOT NULL AND TRIM(ma.ma_cliente) != ''
        THEN TRIM(ma.ma_cliente)
        ELSE 'Cliente non specificato'
        END AS v_cliente,

    ma.ma_tipo as ma_tipo,
    ROUND(ma.ma_importo_totale::numeric, 2) AS ma_importo_totale,
    COALESCE(pa.totale_pagato, 0.00) AS v_pagato,
    COALESCE(pa.totale_saldo, 0.00) AS v_saldo

FROM movimenti_attivi ma
         LEFT JOIN payment_aggregates pa ON (
    ma.ma_numero = pa.rma_numero
        AND ma.ma_data = pa.rma_data
    )
WHERE user_id = auth.uid()
ORDER BY
    ma.ma_data DESC,
    ma.ma_numero;



DROP VIEW IF EXISTS movimenti_passivi_overview;
CREATE VIEW movimenti_passivi_overview WITH (security_invoker = true) AS
    WITH payment_aggregates AS (
    SELECT
    rmp_numero,
    rmp_data,

    -- Total amount already paid (where payment date is not null)
    ROUND(COALESCE(SUM(
    CASE
    WHEN rmp_data_pagamento IS NOT NULL
    THEN rmp_importo_pagamento
    ELSE 0
    END
), 0)::numeric, 2) AS totale_pagato,

    -- Total amount still unpaid (where payment date is null)
    ROUND(COALESCE(SUM(
    CASE
    WHEN rmp_data_pagamento IS NULL
    THEN rmp_importo_pagamento
    ELSE 0
    END
), 0)::numeric, 2) AS totale_saldo

    FROM rate_movimenti_passivi
    WHERE user_id = auth.uid()
    GROUP BY rmp_numero, rmp_data
)
SELECT

    mp.mp_data AS data,

    mp.mp_numero AS numero,

    CASE
        WHEN mp.mp_fornitore IS NOT NULL AND TRIM(mp.mp_fornitore) != ''
        THEN TRIM(mp.mp_fornitore)
        ELSE 'Fornitore non specificato'
        END AS fornitore,

    ROUND(mp.mp_importo_totale::numeric, 2) AS totale,

    COALESCE(pa.totale_pagato, 0.00) AS pagato,

    COALESCE(pa.totale_saldo, 0.00) AS saldo

FROM movimenti_passivi mp
         LEFT JOIN payment_aggregates pa ON (
    mp.mp_numero = pa.rmp_numero
        AND mp.mp_data = pa.rmp_data
    )
WHERE user_id = auth.uid()
ORDER BY
    mp.mp_data DESC,
    mp.mp_numero;



-- Shows monthly totals for sales invoices, purchase invoices, and balance
DROP VIEW IF EXISTS monthly_invoice_summary;
CREATE VIEW monthly_invoice_summary
       WITH (security_invoker = true) AS
WITH monthly_sales AS (
    SELECT
        EXTRACT(MONTH FROM fe_data_documento) AS mese,
        ROUND(SUM(fe_importo_totale_documento)::numeric, 2) AS importo_vendite
    FROM fatture_emesse
    WHERE EXTRACT(YEAR FROM fe_data_documento) = EXTRACT(YEAR FROM CURRENT_DATE)
          AND user_id = auth.uid()
    GROUP BY EXTRACT(MONTH FROM fe_data_documento)
),
monthly_purchases AS (
    SELECT
        EXTRACT(MONTH FROM fr_data_documento) AS mese,
        ROUND(SUM(fr_importo_totale_documento)::numeric, 2) AS importo_acquisti
    FROM fatture_ricevute
    WHERE EXTRACT(YEAR FROM fr_data_documento) = EXTRACT(YEAR FROM CURRENT_DATE)
          AND user_id = auth.uid()
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
    ROUND(COALESCE(dicembre, 0.00)::numeric, 2) AS dicembre
--     ROUND((COALESCE(gennaio, 0) + COALESCE(febbraio, 0) + COALESCE(marzo, 0) + COALESCE(aprile, 0) +
--            COALESCE(maggio, 0) + COALESCE(giugno, 0) + COALESCE(luglio, 0) + COALESCE(agosto, 0) +
--            COALESCE(settembre, 0) + COALESCE(ottobre, 0) + COALESCE(novembre, 0) + COALESCE(dicembre, 0))::numeric, 2) AS totale_anno
FROM (
         -- Sales invoices row
         SELECT
             'Fatture Emesse' AS tipo_fattura,
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
             'Fatture Ricevute' AS tipo_fattura,
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



DROP VIEW IF EXISTS monthly_altri_movimenti_summary;
CREATE VIEW monthly_altri_movimenti_summary WITH (security_invoker = true) AS
WITH
monthly_sales AS (
    SELECT
        EXTRACT(MONTH FROM ma_data) AS mese,
        ROUND(SUM(ma_importo_totale)::numeric, 2) AS importo_vendite
    FROM movimenti_attivi
    WHERE EXTRACT(YEAR FROM ma_data) = EXTRACT(YEAR FROM CURRENT_DATE)
    AND user_id = auth.uid()
    GROUP BY EXTRACT(MONTH FROM ma_data)
),
monthly_purchases AS (
    SELECT
        EXTRACT(MONTH FROM mp_data) AS mese,
        ROUND(SUM(mp_importo_totale)::numeric, 2) AS importo_acquisti
    FROM movimenti_passivi
    WHERE EXTRACT(YEAR FROM mp_data) = EXTRACT(YEAR FROM CURRENT_DATE)
    AND user_id = auth.uid()
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



-- The final columns have to be named with the same name of
-- public.casse fields, so that I can do the delete.
DROP VIEW IF EXISTS casse_summary;
CREATE VIEW casse_summary WITH (security_invoker = true) AS
SELECT DISTINCT
    t1.nome_cassa as c_nome_cassa,
    t1.iban_cassa as c_iban_cassa,
    t2.c_descrizione_cassa
FROM (
         -- I need to filter out rows that are all null because the union will take
         -- null row, try to match it with something that will not exist, so it will
         -- match with null, so I'll get an empty row with all nulls
         SELECT rfe_nome_cassa as nome_cassa, rfe_iban_cassa as iban_cassa
         FROM rate_fatture_emesse
         WHERE user_id = auth.uid() AND (rfe_nome_cassa IS NOT NULL OR rfe_iban_cassa IS NOT NULL)
         UNION
         SELECT c_nome_cassa as nome_cassa, c_iban_cassa as iban_cassa
         FROM casse
         WHERE user_id = auth.uid() AND (c_nome_cassa IS NOT NULL OR c_iban_cassa IS NOT NULL)
     ) t1
         LEFT JOIN casse t2
                   ON (t1.nome_cassa = t2.c_nome_cassa AND t1.iban_cassa = t2.c_iban_cassa)
ORDER BY t1.nome_cassa, t1.iban_cassa;



-- This is for creating the single column of casse to select options from
DROP VIEW IF EXISTS casse_options;
CREATE VIEW casse_options WITH (security_invoker = true) AS
SELECT DISTINCT
    COALESCE(t2.c_descrizione_cassa, t1.nome_cassa, t1.iban_cassa) as cassa
FROM (
         SELECT rfe_nome_cassa as nome_cassa, rfe_iban_cassa as iban_cassa
         FROM rate_fatture_emesse
         WHERE user_id = auth.uid() AND (rfe_nome_cassa IS NOT NULL OR rfe_iban_cassa IS NOT NULL)
         UNION
         SELECT c_nome_cassa as nome_cassa, c_iban_cassa as iban_cassa
         FROM casse
         WHERE user_id = auth.uid() AND (c_nome_cassa IS NOT NULL OR c_iban_cassa IS NOT NULL)
     ) t1
         LEFT JOIN casse t2 ON (t1.nome_cassa = t2.c_nome_cassa AND t1.iban_cassa = t2.c_iban_cassa)
ORDER BY cassa;