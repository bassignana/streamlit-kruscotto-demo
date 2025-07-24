-- Users table (custom, not auth.users)
CREATE TABLE public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email character varying NOT NULL UNIQUE,
  password_hash character varying NOT NULL,
  full_name character varying NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  last_login timestamp with time zone,
  is_active boolean DEFAULT true,
  CONSTRAINT users_pkey PRIMARY KEY (id)
);

-- Invoices table
CREATE TABLE public.invoices (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  invoice_number character varying NOT NULL,
  type character varying NOT NULL CHECK (type::text = ANY (ARRAY['sale'::character varying, 'purchase'::character varying]::text[])),
  client_supplier character varying NOT NULL,
  currency character varying DEFAULT 'EUR'::character varying,
  total_amount numeric NOT NULL,
  document_date date NOT NULL,
  due_date date,
  xml_content text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT invoices_pkey PRIMARY KEY (id),
  CONSTRAINT invoices_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);

-- User data table
CREATE TABLE public.user_data (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  data jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_data_pkey PRIMARY KEY (id),
  CONSTRAINT user_data_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);