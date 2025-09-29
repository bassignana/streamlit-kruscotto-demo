-- Pattern: maybe keeping in the database at least all the logic that I need to insert lines and populate all
-- the tables correctly can be useful.

-- How do I tell pg_prove what connection to use?
-- Impersonate user with extension or use explicit user ids?

-- If there is only one invoice, it is correctly picked up by all views and tables.

-- Since this is a transaction I can test it right away here right?
BEGIN;
SELECT plan(2);

DELETE FROM fatture_emesse;
DELETE FROM rate_fatture_emesse;
DELETE FROM fatture_ricevute;
DELETE FROM rate_fatture_ricevute;
DELETE FROM movimenti_attivi;
DELETE FROM rate_movimenti_attivi;
DELETE FROM movimenti_passivi;
DELETE FROM rate_movimenti_passivi;
DELETE FROM casse;

INSERT
INTO fatture_emesse (user_id,
                     fe_partita_iva_prestatore,
                     fe_numero_fattura,
                     fe_data_documento,
                     fe_importo_totale_documento)
VALUES (get_uuid('test3@gmail.com'), '12345678900', 1, NOW()::date, 100.00);

-- TODO; insert the inser_record function.

-- TODO: Here more then the triggers, which is none the less good to test, I should test the term table.
SELECT isnt(id, NULL, 'Trigger must insert not NULL value.'),
       isnt(created_at, NULL, 'Trigger must insert not NULL value.'),
       isnt(updated_at, NULL, 'Trigger must insert not NULL value.')
FROM fatture_emesse
WHERE user_id = get_uuid('test3@gmail.com');

-- SELECT gennaio + febbraio + marzo + aprile + maggio + giugno + luglio + agosto + settembre + ottobre + novembre +
--        dicembre FROM monthly_invoice_summary where tipo_fattura = 'Saldo';

SELECT is(gennaio + febbraio + marzo + aprile + maggio + giugno + luglio + agosto + settembre + ottobre + novembre +
          dicembre::numeric,
          100.00,
          'Total must be correct.')
FROM monthly_invoice_summary where tipo_fattura = 'Saldo';

ROLLBACK;
