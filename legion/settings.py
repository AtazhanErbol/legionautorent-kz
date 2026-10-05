"""Environment-specific settings entrypoint; existing DB schema/data are retained."""
import importlib
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(os.getenv('LEGION_ENV_FILE') or Path(__file__).resolve().parent.parent / '.env')
name=os.getenv('ENVIRONMENT','development')
if name not in ('development','staging','production','testing'):
    raise RuntimeError('ENVIRONMENT must be development, staging, production or testing.')
module=importlib.import_module(f'legion.config.{name}')
globals().update({key:value for key,value in vars(module).items() if key.isupper()})
