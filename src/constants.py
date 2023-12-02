from pathlib import Path

BASE_DIR = Path(__file__).parent

MAIN_DOC_URL = 'https://docs.python.org/3/'
PEP_DOC_URL = 'https://peps.python.org/'

DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'

PEP_801_STATUS = 'Informational, Active'

# Без этой константы не проходят тесты
EXPECTED_STATUS = None
