
-- Drop tables in correct order (foreign keys first)
DROP TABLE IF EXISTS user_data CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS fatture_emesse CASCADE;