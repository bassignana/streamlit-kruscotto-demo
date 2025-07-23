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

# 2. DB
Here I prefer a manage supabase account in order to avoid to 
manage the local supabase instance.

# 3. Project automation
Focus on generating code to faster iteration.



