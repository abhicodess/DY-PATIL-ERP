import json
import os
import sys

# Add the project directory to sys.path
sys.path.append(os.getcwd())

from utils.pg_wrapper import qry

def inspect_schema():
    tables = qry("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    schema = {}
    for table in tables:
        name = table['table_name']
        columns = qry(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{name}'")
        schema[name] = [dict(c) for c in columns]
    return schema

if __name__ == "__main__":
    print(json.dumps(inspect_schema(), indent=2))
