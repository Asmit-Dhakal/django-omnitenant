import re
from django.core.exceptions import ValidationError

PGSQL_VALID_SCHEMA_NAME = re.compile(r"^(?!pg_).{1,63}$", re.IGNORECASE)


def is_valid_schema_name(name):
    return PGSQL_VALID_SCHEMA_NAME.match(name)


def _check_schema_name(name):
    if not is_valid_schema_name(name):
        raise ValidationError("Invalid string used for the schema name.")
