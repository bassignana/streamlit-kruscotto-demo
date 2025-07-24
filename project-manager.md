# 1. Snippets
Run the following code snippets to 'automate' running the project.
In pycharm there is a bug in running fragments.

Initialized with: 
uv init --python 3.13

```bash
# Before running any snippet,
# ensure that the pwd is correct.
pwd
```

Add packages with versioning:
```bash
uv add 'streamlit==1.47.0'
uv add 'pandas==2.3.0'
uv add 'supabase==2.16'
uv add 'plotly==6.2'
```

Manage local development inside the venv
```bash
source .venv/bin/activate
which python
python --version
```

Deploy procedure
```bash
# 1. Update the requirements. The changes will be picked up by the
#    Streamlit community Cloud. 
uv export --format requirements-txt --output-file requirements.txt

# 2. Commit the changes.
```

For the list of COMMON and UNCOMMON tags between all invoices:
python3 invoice_common_tags.py fatture_emesse/ fatture_ricevute 

# 2. DB
Here I prefer a manage supabase account in order to avoid to 
manage the local supabase instance.


# 3. Project automation
Focus on generating code to faster iteration.

NOTE: since I cannot run raw sql directly in supabase from
the python API, I use the following workaround where I have
to create the following procedure manually once.

```sql
-- Run this ONCE in Supabase SQL Editor
-- Allows Python script to execute any SQL
CREATE OR REPLACE FUNCTION exec_sql(sql_query TEXT)
RETURNS TEXT AS $$
BEGIN
    EXECUTE sql_query;
    RETURN 'OK';
EXCEPTION
    WHEN OTHERS THEN
        RETURN 'ERROR: ' || SQLERRM;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

then I can use
Full reset with test data
python reset_db.py
Reset without test data  
python reset_db.py --noseed

test user and credentials in secrets.toml


[x] Add RLS to the below.
[] Verify what index I really need.
[] Ask in chat Invoice Persistene in Supabase:
- add soft delete
- why the REF on user_id? to check? how checks works?
- ADD ALL rls to specify all clause in one statement CRUD
- various thing like type, CHECK, UNIQUE contraints etc...
- How to test and benchmark concurrency and not-locking claims (generate scirpt from CREATE)
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    invoice_number VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('sale', 'purchase')),
    client_supplier VARCHAR(255) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    total_amount DECIMAL(15,2) NOT NULL,
    document_date DATE NOT NULL,
    due_date DATE,
    xml_content TEXT, -- Store original XML
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Compound unique constraint
    UNIQUE(user_id, invoice_number, type)
);

-- Essential indexes
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_user_date ON invoices(user_id, document_date);
CREATE INDEX IF NOT EXISTS idx_invoices_type ON invoices(user_id, type);

CREATE POLICY "Users can manage own data" ON your_table_name
    FOR ALL USING (auth.uid() = user_id);
```

[] create a basic auth template for streamlit for automatic auth 
   (Supa auth chat), that works for registering users without 
   confirmation email, but with pwd recovery already setup 
   (streamlit-app-authnotworkding) for an example.

[] get create and rules for auth tables

[] implement soft delete in both front and backend
``` python
def soft_delete_invoice(supabase: Client, invoice_id: str):
    """Soft delete an invoice"""
    try:
        result = supabase.table('invoices').update({
            'deleted_at': datetime.now().isoformat()
        }).eq('id', invoice_id).execute()
        
        return True, "Invoice deleted successfully"
    except Exception as e:
        return False, f"Error deleting invoice: {str(e)}"

def get_active_invoices(supabase: Client, user_id: str):
    """Get only non-deleted invoices"""
    return supabase.table('invoices')\
        .select('*')\
        .eq('user_id', user_id)\
        .is_('deleted_at', 'null')\
        .execute()

def restore_invoice(supabase: Client, invoice_id: str):
    """Restore a soft-deleted invoice"""
    return supabase.table('invoices').update({
        'deleted_at': None
    }).eq('id', invoice_id).execute()
```

[x] implement auto paging structure
creation so that in development
it is easy to put each single feature in a page. 
NOTE: do not call the folder 'pages',
that could be in conflict with the 
default streamlit behaviour.

[] remember that I can add material icons to pages 
st.Page("dashboard.py", title="Dashboard", icon=":material/search:")

[] Se avessi 2 tabelle, una per tutte le fatture
   emesse, e una per quelle ricevute. Eventualmente 4 tabelle se alle 2 aggiungo
   delle scadenze in altre tabelle.
   Poi creo un file di configurazione che associa,
   a ciascun campo nella tabella, un relativo tag xml. 
   Da li potrei autogenerare il processor xml,
   e i vari componenti streamlit per l'input e
   la visualizzazione.
   Ed eventuali test.


# 4. Business logic
Distinzione tra fatture emesse e ricevute
