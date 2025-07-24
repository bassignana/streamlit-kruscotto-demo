# reset_db.py (FIXED VERSION)
"""
Database reset script using Supabase client
Requires exec_sql function to be created once in Supabase SQL Editor
"""

import argparse
import os
import toml
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

def main():
    parser = argparse.ArgumentParser(description='Reset database')
    parser.add_argument('--noseed', action='store_true', 
                       help='Skip seed data insertion')
    args = parser.parse_args()
    
    print("🔄 Starting database reset...")
    
    # Test connection
    try:
        client = get_supabase_client()
        print("✅ Supabase connection established")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Execute SQL files in order
    sql_files = get_sql_files()
    
    for sql_file in sql_files:
        if should_skip_file(sql_file, args.noseed):
            print(f"⏭️  Skipping {sql_file}")
            continue
            
        print(f"📄 Executing {sql_file}...")
        try:
            execute_sql_file(sql_file)
            print(f"✅ Completed {sql_file}")
        except Exception as e:
            print(f"❌ Error in {sql_file}: {str(e)}")
            response = input("Continue with remaining files? (y/N): ")
            if response.lower() != 'y':
                break
    
    print("🎉 Database reset complete!")

def get_sql_files():
    """Get SQL files in execution order"""
    return [
        "sql/01_drop_tables.sql",
        "sql/02_create_tables.sql", 
        "sql/03_create_indexes.sql",
        "sql/04_create_policies.sql",
        "sql/05_seed_data.sql"
    ]

def should_skip_file(filename, noseed_flag):
    """Skip seed files if --noseed flag provided"""
    return noseed_flag and "seed" in filename.lower()

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
    
    # Split into individual statements
    statements = split_sql_statements(sql_content)
    
    for i, statement in enumerate(statements):
        if statement.strip():
            try:
                # FIXED: Proper result handling for Supabase RPC
                result = client.rpc('exec_sql', {'sql_query': statement}).execute()
                
                # Check the actual result structure
                if hasattr(result, 'data') and result.data:
                    response_data = result.data
                    # Handle different response formats
                    if isinstance(response_data, list) and len(response_data) > 0:
                        response_value = response_data[0]
                    else:
                        response_value = response_data
                    
                    # Check if the function returned an error
                    if isinstance(response_value, str) and response_value.startswith('ERROR:'):
                        raise Exception(response_value)
                        
                print(f"   📝 Statement {i+1}/{len(statements)} executed")
                
            except Exception as e:
                print(f"   ❌ Statement {i+1} failed: {str(e)}")
                raise

def split_sql_statements(sql_content):
    """Split SQL content into individual statements"""
    # Remove comments and split by semicolon
    lines = []
    for line in sql_content.split('\n'):
        line = line.strip()
        # Skip empty lines and comments
        if line and not line.startswith('--'):
            lines.append(line)
    
    content = ' '.join(lines)
    statements = [stmt.strip() for stmt in content.split(';')]
    return [stmt for stmt in statements if stmt]

if __name__ == "__main__":
    main()