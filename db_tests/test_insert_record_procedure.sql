-- select set_config(
--                'request.jwt.claims',
--                '{
--                  "sub": "86eda584-e990-4e13-9d93-d61b7811da8e",
--                  "role": "authenticated",
--                  "email": "utest0@gmail.com"
--                }',
--                true
--        );
-- select current_setting('request.jwt.claims', true);
-- select auth.uid();

begin;

select plan(2);

delete from fatture_ricevute where user_id = get_uuid('utest0@gmail.com');
delete from rate_fatture_ricevute where user_id = get_uuid('utest0@gmail.com');

select insert_record(
               'fatture_ricevute'::text,
               '{
                 "user_id": "utest0@gmail.com",
                 "fr_partita_iva_prestatore": "12345678901",
                 "fr_numero_fattura": "INV-2024-045",
                 "fr_data_documento": "2024-08-20",
                 "fr_importo_totale_documento": 2000,
                 "fr_denominazione_prestatore": "Studio Rossi Srl"
               }'::jsonb,
               'rate_fatture_ricevute'::text,
               ARRAY[
                   '{
                     "user_id": "utest0@gmail.com",
                     "rfr_partita_iva_prestatore": "12345678901",
                     "rfr_numero_fattura": "INV-2024-045",
                     "rfr_data_documento": "2024-08-20",
                     "rfr_data_scadenza_pagamento": "2024-10-10",
                     "rfr_importo_pagamento_rata": 1000,
                     "rfr_nome_cassa": "Conto Corrente Principale",
                     "rfr_iban_cassa": "IT60X0542811101000000123456",
                     "rfr_notes": "Pagamento prima rata fattura fornitore",
                     "rfr_data_pagamento_rata": null
                   }'::JSONB,
                   '{
                     "user_id": "utest0@gmail.com",
                     "rfr_partita_iva_prestatore": "12345678901",
                     "rfr_numero_fattura": "INV-2024-045",
                     "rfr_data_documento": "2024-08-20",
                     "rfr_data_scadenza_pagamento": "2024-02-10",
                     "rfr_importo_pagamento_rata": 1000,
                     "rfr_nome_cassa": "Conto Corrente Principale",
                     "rfr_iban_cassa": "IT60X0542811101000000123456",
                     "rfr_notes": "Pagamento seconda rata fattura fornitore",
                     "rfr_data_pagamento_rata": null
                   }'::JSONB
                   ],
                    -- Note: I could also modify the function to take a uuid.
               get_uuid('utest0@gmail.com')::text
       );

prepare condition_one as select rfr_nome_cassa, rfr_iban_cassa from rate_fatture_ricevute where user_id = get_uuid('utest0@gmail.com');

select set_eq(
    'condition_one',
    'select * from (values (null,null), (null, null))',
    'Cassa and Iban are valued to null in both terms'
      );


-- be sure to cast the count as int, otherwise there is a mismatch between bigInt and 1::int
-- I don't think I can use the prepared statement in place of the select here...
select is(
    (select count(*) from fatture_ricevute where user_id = get_uuid('utest0@gmail.com'))::int,
    1,
    'Inserted exactly one row in fatture_ricevute'
       );

deallocate condition_one;
select * from finish();

rollback;