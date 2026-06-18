with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    has_query = any(k in line for k in ['qry(', 'qone(', 'exe('])
    has_q_placeholder = '=?' in line or 'IN (?' in line
    has_join_question = '"?"' in line or "'?'" in line
    if (has_query and has_q_placeholder) or has_join_question:
        print(f"Line {i}: {line.rstrip()}")
