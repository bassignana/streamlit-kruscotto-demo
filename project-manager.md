```bash
pwd
```

Initialized with: 
uv init --python 3.13

Add packages with versioning:
```bash
uv add 'streamlit==1.47.0'
```

Manage local development inside the venv
```bash
source .venv/bin/activate
which python
python --version
```

Dependencies:
```bash
uv add 'pandas==2.3.0'
uv add 'supabase==2.16'
uv add 'plotly==6.2'

```

Deploy procedure
```bash
# 1. Update the requirements. The changes will be picked up by the
#    Streamlit community Cloud. 
uv export --format requirements-txt --output-file requirements.txt

# 2. Commit the changes.
```

Initialize local instance of supabase
```bash
npm install supabase
npx supabase init

# start docker deamon and then
npx supabase start
```
