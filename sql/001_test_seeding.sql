-- test3 user_id: '0d15a504-9fff-49e0-8297-765428ac94c9'
-- partita iva azienda: '12345678909'
-- partita iva esterna: '09876543212'
-- data format in 'yyyy-mm-dd'

begin;
delete from fatture_emesse where user_id = '0d15a504-9fff-49e0-8297-765428ac94c9';
insert into fatture_emesse (user_id, fe_partita_iva_prestatore, fe_numero_fattura, fe_data_documento,
                            fe_importo_totale_documento, fe_partita_iva_committente, fe_codice_fiscale_committente,
                            fe_nome_committente, fe_cognome_committente, fe_denominazione_committente)
values
    ('0d15a504-9fff-49e0-8297-765428ac94c9', '12345678909', 'FAT001/2025', '2025-01-01', 1000.01, '09876543212', 'TSTMRA85M01H501T', 'Test Mario', 'Test Rossi', NULL),
    ('0d15a504-9fff-49e0-8297-765428ac94c9', '12345678909', 'FAT002/2025', '2025-02-01', 1000.01, NULL, NULL, NULL, NULL, 'Test Company S.r.l.'),
    ('0d15a504-9fff-49e0-8297-765428ac94c9', '12345678909', 'FAT003/2025', '2025-03-01', 1000.01, '09876543212', 'TSTMRA85M01H501T', 'Test Mario', 'Test Rossi', NULL),
    ('0d15a504-9fff-49e0-8297-765428ac94c9', '12345678909', 'FAT004/2025', '2025-04-01', 1000.01, NULL, NULL, NULL, NULL, 'Test Company S.r.l.'),
    ('0d15a504-9fff-49e0-8297-765428ac94c9', '12345678909', 'FAT005/2025', '2025-05-01', 1000.01, '09876543212', 'TSTMRA85M01H501T', 'Test Mario', 'Test Rossi', NULL);
commit;