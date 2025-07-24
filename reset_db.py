# reset_db.py (UPDATED WITH SECRETS-BASED CREDENTIALS)
"""
Database reset script using custom users table
Test user credentials loaded from secrets.toml
"""

import argparse
import os
import toml
import hashlib
from pathlib import Path
from supabase import create_client

def load_secrets():
    """Load secrets from .streamlit/secrets.toml"""
    secrets_path = Path(".streamlit/secrets.toml")
    
    if not secrets_path.exists():
        raise FileNotFoundError("Missing .streamlit/secrets.toml file")
    
    return toml.load(secrets_path)

def get_supabase_client():
    """Create Supabase client with service role privileges"""
    secrets = load_secrets()
    
    url = secrets.get("SUPABASE_URL")
    service_key = secrets.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not service_key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in secrets.toml")
    
    return create_client(url, service_key)

def hash_password(password):
    """Simple password hashing (you might want to use bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_test_user():
    """Create test user in custom users table using credentials from secrets"""
    client = get_supabase_client()
    secrets = load_secrets()
    
    # Load test user credentials from secrets
    test_email = secrets.get("TEST_USER_EMAIL")
    test_password = secrets.get("TEST_USER_PASSWORD") 
    test_full_name = secrets.get("TEST_USER_FULL_NAME", "Test User")
    
    if not test_email or not test_password:
        raise ValueError("Missing TEST_USER_EMAIL or TEST_USER_PASSWORD in secrets.toml")
    
    try:
        # Create test user in your custom users table
        result = client.table('users').insert({
            "email": test_email,
            "password_hash": hash_password(test_password),
            "full_name": test_full_name,
            "is_active": True
        }).execute()
        
        if result.data:
            user_id = result.data[0]['id']
            print(f"✅ Test user created: {user_id}")
            print(f"🔑 Login credentials: {test_email} / {test_password}")
            return user_id
        else:
            print("❌ User creation failed - no data returned")
            return None
        
    except Exception as e:
        print(f"❌ User creation failed: {e}")
        # Try to find existing user
        try:
            result = client.table('users').select("id").eq("email", test_email).execute()
            if result.data:
                user_id = result.data[0]['id']
                print(f"✅ Using existing test user: {user_id}")
                print(f"🔑 Login credentials: {test_email} / {test_password}")
                return user_id
        except:
            pass
        
        return None

def execute_seed_data_with_user(user_id):
    """Execute seed data with actual user ID"""
    seed_file = "sql/05_seed_data.sql"
    
    if not os.path.exists(seed_file):
        print(f"⚠️  Seed file not found: {seed_file}")
        return
        
    with open(seed_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Replace placeholder with actual user ID
    sql_content = sql_content.replace('USER_ID_PLACEHOLDER', str(user_id))
    
    print(f"📄 Executing seed data for user: {user_id}")
    execute_sql(sql_content)

def main():
    parser = argparse.ArgumentParser(description='Reset database')
    parser.add_argument('--noseed', action='store_true', 
                       help='Skip seed data insertion')
    args = parser.parse_args()
    
    print("🔄 Starting database reset...")
    
    # Test connection and secrets
    try:
        client = get_supabase_client()
        secrets = load_secrets()
        
        # Validate test user credentials exist
        if not secrets.get("TEST_USER_EMAIL") or not secrets.get("TEST_USER_PASSWORD"):
            print("❌ Missing test user credentials in secrets.toml")
            print("💡 Add TEST_USER_EMAIL and TEST_USER_PASSWORD to .streamlit/secrets.toml")
            return
            
        print("✅ Supabase connection established")
        print(f"✅ Test user credentials loaded from secrets")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return
    
    # Execute structure files first
    structure_files = [
        "sql/01_drop_tables.sql",
        "sql/02_create_tables.sql", 
        "sql/03_create_indexes.sql",
        "sql/04_create_policies.sql"
    ]
    
    for sql_file in structure_files:
        print(f"📄 Executing {sql_file}...")
        try:
            execute_sql_file(sql_file)
            print(f"✅ Completed {sql_file}")
        except Exception as e:
            print(f"❌ Error in {sql_file}: {str(e)}")
            response = input("Continue with remaining files? (y/N): ")
            if response.lower() != 'y':
                return
    
    print("👤 Creating test user...")
    test_user_id = create_test_user()

    # Handle seed data separately with user creation
    if not args.noseed:
        
        if test_user_id:
            try:
                execute_seed_data_with_user(test_user_id)
                print("✅ Seed data completed")
            except Exception as e:
                print(f"❌ Seed data failed: {e}")
        else:
            print("⚠️  Skipping seed data - no test user created")
    
    print("🎉 Database reset complete!")

def execute_sql_file(filepath):
    """Execute SQL file contents"""
    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath} - skipping")
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_content = f.read().strip()
    
    if not sql_content:
        print(f"⚠️  Empty file: {filepath} - skipping")
        return
    
    execute_sql(sql_content)

def execute_sql(sql_content):
    """Execute SQL using the manually created exec_sql function"""
    client = get_supabase_client()
    
    statements = split_sql_statements(sql_content)
    
    for i, statement in enumerate(statements):
        if statement.strip():
            try:
                result = client.rpc('exec_sql', {'sql_query': statement}).execute()
                print(f"   📝 Statement {i+1}/{len(statements)} executed")
            except Exception as e:
                print(f"   ❌ Statement {i+1} failed: {str(e)}")
                raise

def split_sql_statements(sql_content):
    """Split SQL content into individual statements"""
    lines = []
    for line in sql_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('--'):
            lines.append(line)
    
    content = ' '.join(lines)
    statements = [stmt.strip() for stmt in content.split(';')]
    return [stmt for stmt in statements if stmt]

if __name__ == "__main__":
    main()