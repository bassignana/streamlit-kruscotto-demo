-- NOTE: here I'm using pgtap for seeding, which is not a good thing to do, they say.
begin;
select plan(0);

delete from fatture_emesse where user_id = get_uuid('utest0@gmail.com');
delete from fatture_ricevute where user_id = get_uuid('utest0@gmail.com');
delete from movimenti_attivi where user_id = get_uuid('utest0@gmail.com');
delete from movimenti_passivi where user_id = get_uuid('utest0@gmail.com');
delete from rate_fatture_emesse where user_id = get_uuid('utest0@gmail.com');
delete from rate_fatture_ricevute where user_id = get_uuid('utest0@gmail.com');
delete from rate_movimenti_attivi where user_id = get_uuid('utest0@gmail.com');
delete from rate_movimenti_passivi where user_id = get_uuid('utest0@gmail.com');
delete from casse where user_id = get_uuid('utest0@gmail.com');

-- Upsert because the row may not exist.
insert into user_data (user_id, ud_codice_fiscale, ud_partita_iva)
values (
           get_uuid('utest0@gmail.com'),
           'test',
           '12345678900'
       )
on conflict (user_id) do update
    set ud_codice_fiscale = excluded.ud_codice_fiscale,
        ud_partita_iva = excluded.ud_partita_iva;

end;