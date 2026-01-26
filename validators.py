"""
Validators for django-omnitenant

This module provides validation functions for schema names, DNS labels, and domain names
used in multi-tenant configurations. These validators ensure that tenant identifiers,
schemas, and domains conform to their respective system requirements.

Validators in this module:
    - is_valid_schema_name: Check if a string is a valid PostgreSQL schema name
    - _check_schema_name: Raise ValidationError if schema name is invalid
    - validate_dns_label: Validate individual DNS labels (RFC 1034/1035)
    - validate_domain_name: Validate fully qualified domain names (FQDN)

Usage:
    ```python
    from django_omnitenant.validators import (
        is_valid_schema_name,
        validate_dns_label,
        validate_domain_name,
    )

    # Check schema validity
    if is_valid_schema_name("my_tenant_schema"):
        print("Valid schema name")

    # Validate DNS label
    try:
        validate_dns_label("subdomain")
    except ValidationError as e:
        print(f"Invalid label: {e}")

    # Validate full domain
    try:
        validate_domain_name("tenant.example.com")
    except ValidationError as e:
        print(f"Invalid domain: {e}")
    ```

Django Integration:
    These validators can be used in Django model fields to automatically validate data:

    ```python
    from django.db import models
    from django_omnitenant.validators import validate_domain_name, validate_dns_label

    class Domain(models.Model):
        name = models.CharField(
            max_length=253,
            validators=[validate_domain_name],
        )
        subdomain = models.CharField(
            max_length=63,
            validators=[validate_dns_label],
        )
    ```

Standards and References:
    - PostgreSQL Schema Names: PostgreSQL documentation
    - DNS Labels: RFC 1034, RFC 1035
    - Domain Names: RFC 1123 (updates to RFC 1035)
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# PostgreSQL Schema Name Validation Pattern
# ==========================================

PGSQL_VALID_SCHEMA_NAME = re.compile(r"^(?!pg_).{1,63}$", re.IGNORECASE)
"""
Regex pattern for validating PostgreSQL schema names.

Pattern Components:
    ^       - Start of string
    (?!pg_) - Negative lookahead: does NOT start with 'pg_' (reserved prefix)
    .{1,63} - Between 1 and 63 characters (any character except newline)
    $       - End of string
    
Flags:
    re.IGNORECASE - Case-insensitive matching (pg_, PG_, Pg_ all rejected)

PostgreSQL Schema Name Rules:
    - Max length: 63 characters (PostgreSQL identifier limit)
    - Cannot start with 'pg_' (reserved for system schemas)
    - Case-insensitive (internally stored as lowercase)
    - Alphanumeric + underscore typically allowed (checked by application)

Note:
    This pattern validates basic structure but assumes character set is already
    validated elsewhere. For full validation, characters should be [a-zA-Z0-9_].

Example Matches:
    - "my_schema" ✓
    - "tenant1" ✓
    - "Schema_2024" ✓

Example Non-Matches:
    - "pg_custom" ✗ (reserved prefix)
    - "very_long_schema_name_that_exceeds_63_characters_limit_xyz" ✗ (too long)
    - "" ✗ (empty)
"""


# Schema Name Validators
# =====================


def is_valid_schema_name(name):
    """
    Check if a string is a valid PostgreSQL schema name.

    This is a lightweight check that validates the basic structure of a schema name
    without raising exceptions. Use this for conditional logic or pre-flight checks.

    Args:
        name (str): The schema name to validate

    Returns:
        Match object if valid, None if invalid

    Validation Rules:
        - Must not start with 'pg_' (reserved prefix)
        - Must be between 1 and 63 characters
        - Length checked by regex pattern

    Examples:
        ```python
        from django_omnitenant.validators import is_valid_schema_name

        # Valid names
        is_valid_schema_name("my_tenant")      # Match object (truthy)
        is_valid_schema_name("tenant_1")       # Match object (truthy)
        is_valid_schema_name("a")              # Match object (truthy)

        # Invalid names
        is_valid_schema_name("pg_system")      # None (falsy) - reserved prefix
        is_valid_schema_name("")               # None (falsy) - empty
        is_valid_schema_name("x" * 64)         # None (falsy) - too long
        ```

    Return Type:
        The regex Match object (truthy) for valid names, allowing use in conditionals:

        ```python
        if is_valid_schema_name(tenant_name):
            create_schema(tenant_name)
        else:
            raise ValueError(f"Invalid schema: {tenant_name}")
        ```

    Truthiness:
        ```python
        # Use in boolean context
        valid_name = is_valid_schema_name("tenant")
        if valid_name:  # Truthy for matches
            process_schema(valid_name.group())

        # Or convert to bool explicitly
        if bool(is_valid_schema_name(name)):
            ...
        ```

    Related:
        - _check_schema_name: Raises ValidationError instead
        - convert_to_valid_pgsql_schema_name: Normalizes names to be valid

    Note:
        This function returns a Match object, not a boolean. Check truthiness
        with `if is_valid_schema_name(...)` rather than `== True`.
    """
    # Use regex pattern to validate schema name structure
    return PGSQL_VALID_SCHEMA_NAME.match(name)


def _check_schema_name(name):
    """
    Validate a schema name and raise ValidationError if invalid.

    This is the error-raising version of is_valid_schema_name(). Use this when
    you want to validate input and immediately fail with a clear error message
    if invalid.

    Args:
        name (str): The schema name to validate

    Raises:
        ValidationError: If the schema name is invalid

    Validation Rules:
        - Must not start with 'pg_' (reserved prefix)
        - Must be between 1 and 63 characters
        - Must match PostgreSQL schema name rules

    Examples:
        ```python
        from django_omnitenant.validators import _check_schema_name
        from django.core.exceptions import ValidationError

        # Valid names - no exception
        _check_schema_name("my_tenant")
        _check_schema_name("tenant_1")

        # Invalid names - raise ValidationError
        try:
            _check_schema_name("pg_system")
        except ValidationError as e:
            print(e)  # "Invalid string used for the schema name."

        try:
            _check_schema_name("")
        except ValidationError as e:
            print(e)  # "Invalid string used for the schema name."
        ```

    Error Message:
        Raises with message: "Invalid string used for the schema name."

        This is a generic message suitable for logging but doesn't specify why
        the name is invalid (reserved prefix, too long, empty, etc.).

    Usage in Django Models:
        ```python
        from django.db import models
        from django.core.exceptions import ValidationError
        from django_omnitenant.validators import _check_schema_name

        class Tenant(models.Model):
            schema_name = models.CharField(max_length=63)

            def clean(self):
                super().clean()
                try:
                    _check_schema_name(self.schema_name)
                except ValidationError:
                    raise ValidationError({'schema_name': 'Invalid schema name'})
        ```

    Related:
        - is_valid_schema_name: Non-raising version
        - ValidationError: Django's validation exception

    Internal Use:
        The leading underscore (_check_schema_name) indicates this is a private
        function, primarily for internal use. Consider using public validation
        methods instead when possible.
    """
    # Check if name is valid using the regex validator
    if not is_valid_schema_name(name):
        # Raise ValidationError with descriptive message
        raise ValidationError("Invalid string used for the schema name.")


def validate_dns_label(value):
    """
    Validate a single DNS label according to RFC 1034 and RFC 1035.
    
    A DNS label is a single component of a domain name (e.g., "subdomain" in
    "subdomain.example.com"). This validator ensures each label conforms to
    DNS standards.
    
    DNS Label Rules (RFC 1034/1035):
        - Only letters (a-z, A-Z), digits (0-9), and hyphens (-)
        - Cannot start with a hyphen (-)
        - Cannot end with a hyphen (-)
        - Length between 1 and 63 characters
        - Case-insensitive (internally stored as lowercase)
        
    Args:
        value (str): The DNS label to validate (e.g., "example", "api-v2", "tenant1")
        
    Raises:
        ValidationError: If the label doesn't conform to RFC 1034/1035 standards
        
    Validation Pattern:
        ^(?!-)      - Negative lookahead: NOT starting with hyphen
        [A-Za-z0-9-]{1,63}  - 1-63 characters: letters, digits, hyphens
        (?<!-)$     - Negative lookbehind: NOT ending with hyphen
        
    Examples:
        ```python
        from django_omnitenant.validators import validate_dns_label
        from django.core.exceptions import ValidationError
        
        # Valid labels
        validate_dns_label("example")       # ✓
        validate_dns_label("api")           # ✓
        validate_dns_label("tenant-1")      # ✓
        validate_dns_label("my-api-v2")     # ✓
        validate_dns_label("123")           # ✓
        validate_dns_label("a")             # ✓
        
        # Invalid labels
        try:
            validate_dns_label("-invalid")  # ✗ starts with hyphen
        except ValidationError as e:
            print(e)  # "subdomain is not a valid DNS label."
        
        try:
            validate_dns_label("invalid-")  # ✗ ends with hyphen
        except ValidationError as e:
            print(e)
        
        try:
            validate_dns_label("a_b")       # ✗ underscore not allowed
        except ValidationError as e:
            print(e)
        
        try:
            validate_dns_label("")          # ✗ empty
        except ValidationError as e:
            print(e)
        
        try:
            validate_dns_label("x" * 64)    # ✗ too long (>63 chars)
        except ValidationError as e:
            print(e)
        ```
        
    Use Cases:
        1. Validating subdomains in domain model
        2. Validating DNS records for custom domains
        3. Validating tenant identifiers based on subdomains
        4. Form validation for domain-related input
        5. API parameter validation
        
    Error Message:
        "%(value)s is not a valid DNS label."
        where %(value)s is replaced with the invalid value
        
        Example error for input "invalid-":
        "invalid- is not a valid DNS label."
        
    Django Model Integration:
        ```python
        from django.db import models
        from django_omnitenant.validators import validate_dns_label
        
        class Domain(models.Model):
            subdomain = models.CharField(
                max_length=63,
                validators=[validate_dns_label],
                help_text="e.g., 'api', 'dashboard', 'my-app'"
            )
            
            # Or validate in clean() method
            def clean(self):
                super().clean()
                validate_dns_label(self.subdomain)
        ```
        
    Related:
        - validate_domain_name: For validating full domain names (FQDNs)
        - RFC 1034: https://tools.ietf.org/html/rfc1034
        - RFC 1035: https://tools.ietf.org/html/rfc1035
        
    Notes:
        - Each label in a domain name must pass this validation
        - Hyphens are allowed in the middle but not at start/end
        - DNS is case-insensitive but this validator accepts any case
        - Maximum length per label is 63 characters (DNS standard)
    """
    # Pattern explanation:
    # ^(?!-)           - Start: NOT preceded by hyphen
    # [A-Za-z0-9-]{1,63} - 1-63 chars: letters, digits, hyphens
    # (?<!-)$          - End: NOT followed by hyphen
    
    if not re.match(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$", value):
        # Raise ValidationError with the invalid value in the message
        raise ValidationError(
            _("%(value)s is not a valid DNS label."),
            params={"value": value},
        )


def validate_domain_name(value):
    """
    Validate a fully qualified domain name (FQDN) according to DNS standards.
    
    A fully qualified domain name is a complete domain name with all labels
    (e.g., "api.example.com"). This validator splits the domain into labels
    and validates each one, plus checks total length.
    
    FQDN Validation Rules:
        - Split by dots (.) into labels
        - Each label must be valid per RFC 1034/1035 (see validate_dns_label)
        - Total length must not exceed 253 characters
        - At least one label required
        - At least two labels for typical domain (e.g., "example.com")
        
    Args:
        value (str): The full domain name to validate (e.g., "example.com", "api.example.com")
        
    Raises:
        ValidationError: If the domain doesn't conform to DNS standards
        
    Validation Steps:
        1. Check total length doesn't exceed 253 characters
        2. Split domain by dots into individual labels
        3. Validate each label using validate_dns_label
        
    Examples:
        ```python
        from django_omnitenant.validators import validate_domain_name
        from django.core.exceptions import ValidationError
        
        # Valid domains
        validate_domain_name("example.com")           # ✓
        validate_domain_name("api.example.com")       # ✓
        validate_domain_name("my-app.example.co.uk")  # ✓
        validate_domain_name("a.b.c.d.example.com")   # ✓
        validate_domain_name("localhost")             # ✓ (single label)
        
        # Invalid domains
        try:
            validate_domain_name("example-.com")      # ✗ label ends with hyphen
        except ValidationError as e:
            print(e)
        
        try:
            validate_domain_name("-example.com")      # ✗ label starts with hyphen
        except ValidationError as e:
            print(e)
        
        try:
            validate_domain_name("example.com" + "x" * 300)  # ✗ too long
        except ValidationError as e:
            print(e)  # "... exceeds the maximum length of 253 characters."
        
        try:
            validate_domain_name("example..com")      # ✗ empty label
        except ValidationError as e:
            print(e)
        
        try:
            validate_domain_name("example_site.com")  # ✗ underscore not allowed
        except ValidationError as e:
            print(e)
        ```
        
    Length Limits:
        - Total domain name: 253 characters maximum
        - Individual label: 63 characters maximum (enforced by validate_dns_label)
        - Reason: DNS protocol limitations and standardization
        
    Use Cases:
        1. Validating custom domain input in domain model
        2. Tenant domain name validation
        3. Form validation for custom domain setup
        4. API endpoint parameter validation
        5. Configuration validation
        
    Error Messages:
        Length error:
        "%(value)s exceeds the maximum length of 253 characters."
        
        Label validation error (from validate_dns_label):
        "%(value)s is not a valid DNS label."
        
    Django Model Integration:
        ```python
        from django.db import models
        from django_omnitenant.validators import validate_domain_name
        
        class Domain(models.Model):
            name = models.CharField(
                max_length=253,
                unique=True,
                validators=[validate_domain_name],
                help_text="e.g., example.com or api.example.com"
            )
            
            class Meta:
                db_table = 'domains'
        ```
        
    Form Integration:
        ```python
        from django import forms
        from django_omnitenant.validators import validate_domain_name
        
        class DomainForm(forms.Form):
            domain = forms.CharField(
                validators=[validate_domain_name],
                label="Domain Name",
                help_text="Enter your domain (e.g., example.com)"
            )
        ```
        
    Related:
        - validate_dns_label: For validating individual labels
        - RFC 1035: https://tools.ietf.org/html/rfc1035
        - RFC 1123: https://tools.ietf.org/html/rfc1123
        
    Notes:
        - Domain validation is strict - some applications allow more permissive rules
        - This implements RFC 1034/1035 standard validation
        - Case-insensitive in practice (DNS is case-insensitive)
        - Internationalized domain names (IDN) not supported (use punycode first)
        - Trailing dot (FQDN format) not handled - "example.com" not "example.com."
    """
    # Step 1: Check total length doesn't exceed 253 characters (DNS standard)
    if len(value) > 253:
        raise ValidationError(
            _("%(value)s exceeds the maximum length of 253 characters."),
            params={"value": value},
        )

    # Step 2: Split domain into labels by dots
    # Example: "api.example.com" -> ["api", "example", "com"]
    labels = value.split(".")

    # Step 3: Validate each label against DNS standards
    # This will raise ValidationError if any label is invalid
    for label in labels:
        validate_dns_label(label)
