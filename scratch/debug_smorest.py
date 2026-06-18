import sys
import os
sys.path.insert(0, os.getcwd())

import traceback

try:
    from app import create_app
    app = create_app()
    print("App created successfully!")
except Exception as e:
    tb = sys.exc_info()[2]
    # Trace local variables at each frame in traceback
    for frame in traceback.walk_tb(tb):
        f_code = frame[0].f_code
        f_locals = dict(frame[0].f_locals)
        print(f"\nFrame {f_code.co_name} in {f_code.co_filename}:{frame[0].f_lineno}")
        for k, v in f_locals.items():
            if k in ('response', 'operations', 'spec', 'doc', 'responses', 'res', 'key', 'value'):
                print(f"  {k} = {v} (type: {type(v)})")
    print("\nOriginal exception:")
    traceback.print_exc()
