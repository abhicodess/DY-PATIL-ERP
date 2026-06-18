import os, re

def convert_file(filename):
    if not os.path.exists(filename):
        return
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # We want to replace '?' with '%s', but ONLY in sql queries.
    # What are the contexts of '?' in the app? 
    # Usually: "WHERE id=?", "(?, ?, ?)"
    # A safe regex: replace '?' followed by a comma, parenthesis, or whitespace, 
    # OR preceded by =, <, >, whitespace, (, 
    
    # Actually, simpler: replace all '? ' with '%s ', '?,' with '%s,', '?)' with '%s)'
    # and '?\n' with '%s\n', '?' at end of string with '%s'
    # Or just use re.sub(r'\?', '%s', sql) on the whole file? No, that breaks URL parameters like '/dashboard?id=1'
    
    # Let's find all occurrences of '?' and conditionally replace them.
    # '?' in python is only used in strings.
    # URLs look like '...?xx='
    def replacer(match):
        text = match.group(0)
        # If the 'text' looks like an SQL string, we replace '?' with '%s'
        # An SQL string usually contains SELECT, INSERT, UPDATE, DELETE, WHERE
        if any(keyword in text.upper() for keyword in ['SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ', 'WHERE ', ' FROM ', 'INTO ', 'VALUES ', 'SET ', ' AND ', ' OR ']):
            # only replace '?' if it's not part of a URL (e.g. not followed by a word character and an '=' sign)
            # We can just replace all '?' that are NOT immediately followed by a word char and '='
            # Actually, `?` in SQL is usually followed by `,`, `)`, ` `, or string end.
            new_text = re.sub(r'\?(?![a-zA-Z0-9_]+\=)', '%s', text)
            return new_text
        return text

    # we find string literals and apply replacer
    new_content = re.sub(r'(?:\'{1,3}|\"{1,3})(?:.*?)(?:\'{1,3}|\"{1,3})', replacer, content, flags=re.DOTALL)
    
    # Fix import sqlite3
    new_content = new_content.replace('import sqlite3', 'import psycopg2\nimport psycopg2.extras')
    new_content = new_content.replace('sqlite3.IntegrityError', 'psycopg2.IntegrityError')
    new_content = new_content.replace('sqlite3.Row', 'psycopg2.extras.DictCursor')
    
    if new_content != content:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filename}")

for f in ['app.py', 'cumulative_routes.py', 'results_bp.py', 'v2_features.py', 'fix_sidebar.py']:
    convert_file(f)
