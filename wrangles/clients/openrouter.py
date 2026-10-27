"""OpenRouter's System One-compatible Decisions API.

Reuse the existing transport and strict answer validation until the provider
configuration refactor. Keep provider-specific exceptions at this boundary;
no request bodies, response bodies, or credentials appear in raised errors.
"""

from . import typesafe as _typesafe


class OpenRouterError(RuntimeError):
    """A sanitized OpenRouter failure."""

    def __init__(self, message, *, status_code=None, attempts=None):
        super().__init__(message)
        self.status_code = status_code
        self.attempts = attempts


class OpenRouterResponseError(OpenRouterError):
    """The gateway returned an invalid or incomplete typed response."""


def call_systemone(*, state, questions, model, api_key, url, timeout, retries):
    """Call /api/alpha/decisions using the existing named-question contract.

Confidence and complete probabilities are required by the Wrangles output
contract even though the gateway schema marks them optional. Missing fields
fail validation; this adapter never invents confidence or probabilities.
"""
    try:
        return _typesafe.call_systemone(
            state=state, questions=questions, model=model, api_key=api_key,
            url=url, timeout=timeout, retries=retries,
        )
    except _typesafe.TypesafeError as error:
        error_type = (OpenRouterResponseError
                      if isinstance(error, _typesafe.TypesafeResponseError)
                      else OpenRouterError)
        # The shared adapter already sanitizes these messages. Translate only
        # its provider name, retaining HTTP status and retry-attempt metadata.
        raise error_type(
            str(error).replace("Typesafe", "OpenRouter"),
            status_code=error.status_code, attempts=error.attempts,
        ) from None
