import logging
import os
import re
from urllib.parse import quote, quote_plus

def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def sanitized_provider_message(response, api_key):
    """Log only a provider's message, never its body, headers, URL or details."""
    try:
        body = response.json()
        if isinstance(body, list) and body:
            body = body[0]
        error = body.get("error") if isinstance(body, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
    except (ValueError, TypeError):
        message = None
    if not isinstance(message, str):
        return "Provider returned no structured error message."
    secrets = [api_key]
    secrets.extend(value for key, value in os.environ.items()
                   if re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|DATABASE_URL", key, re.I) and value)
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret:
            for encoded in {secret, quote(secret, safe=""), quote_plus(secret)}:
                message = message.replace(encoded, "[REDACTED]")
    message = re.sub(r"https?://[^\s<>]+", "[URL REDACTED]", message, flags=re.I)
    message = re.sub(r"\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", message, flags=re.I)
    message = re.sub(r"(?i)([\"']?(?:api[_-]?key|access[_-]?token|token|secret|password|authorization|credential)[\"']?\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)", r"\1[REDACTED]", message)
    message = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", message)
    return " ".join(message.split())[:1000]
