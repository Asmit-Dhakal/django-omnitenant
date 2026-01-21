import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
PGSQL_VALID_SCHEMA_NAME = re.compile(r"^(?!pg_).{1,63}$", re.IGNORECASE)


def is_valid_schema_name(name):
    return PGSQL_VALID_SCHEMA_NAME.match(name)


def _check_schema_name(name):
    if not is_valid_schema_name(name):
        raise ValidationError("Invalid string used for the schema name.")




def validate_dns_label(value):
    """
    Validate a single DNS label according to RFC 1034/1035:
    - Only letters, digits, and hyphens.
    - Cannot start or end with a hyphen.
    - Length between 1 and 63 characters.
    """
    if not re.match(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$", value):
        raise ValidationError(
            _("%(value)s is not a valid DNS label."),
            params={"value": value},
        )

def validate_domain_name(value):
    """
    Validate a full domain name (FQDN).
    - Split into labels and validate each one.
    - Total length must not exceed 253 characters.
    """
    if len(value) > 253:
        raise ValidationError(
            _("%(value)s exceeds the maximum length of 253 characters."),
            params={"value": value},
        )

    labels = value.split(".")

    for label in labels:
        validate_dns_label(label)
