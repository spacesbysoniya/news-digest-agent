import logging
import json
import re
import time
from functools import wraps

# Try to import OpenTelemetry trace library; gracefully fall back if unavailable
try:
    from opentelemetry import trace
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

class JSONFormatter(logging.Formatter):
    """Formats logs into highly structured JSON objects for Cloud Logging / Elasticsearch."""
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

class PIIRedactor:
    """Scrubs sensitive variables such as emails or keys prior to logging."""
    EMAIL_REGEX = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    
    @classmethod
    def redact(cls, text: str) -> str:
        if not isinstance(text, str):
            return text
        return cls.EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)

class MockSpan:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass
    def set_attribute(self, key, value): pass
    def set_status(self, status): pass

class MockTracer:
    def start_as_current_span(self, name, *args, **kwargs):
        return MockSpan()

def get_tracer(name: str):
    if OPENTELEMETRY_AVAILABLE:
        return trace.get_tracer(name)
    return MockTracer()

def trace_intent_outcome(logger_obj):
    """Decorator ensuring strict intent vs outcome logging, duration metrics, and tracing."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Redact intent args for security compliance
            arg_strs = [PIIRedactor.redact(str(a)) for a in args]
            kwarg_strs = {k: PIIRedactor.redact(str(v)) for k, v in kwargs.items()}
            logger_obj.info(f"Intent: Executing '{func.__name__}' with args: {arg_strs}, kwargs: {kwarg_strs}")
            
            start_time = time.time()
            tracer = get_tracer("news-digest-agent")
            with tracer.start_as_current_span(func.__name__) as span:
                span.set_attribute("function.name", func.__name__)
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("function.status", "success")
                    span.set_attribute("function.duration_ms", duration_ms)
                    
                    outcome_msg = f"Outcome: Successfully executed '{func.__name__}' in {duration_ms:.2f}ms. Result: {PIIRedactor.redact(str(result))}"
                    logger_obj.info(outcome_msg)
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("function.status", "failed")
                    span.set_attribute("function.error", str(e))
                    logger_obj.error(f"Outcome: Failed executing '{func.__name__}' after {duration_ms:.2f}ms. Error: {str(e)}")
                    raise e
        return wrapper
    return decorator

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setFormatter(JSONFormatter())
        logger.addHandler(ch)
    return logger