DROP TABLE IF EXISTS invoices CASCADE;

-- Remove test users
DELETE FROM auth.users WHERE email LIKE '%@test.example%';