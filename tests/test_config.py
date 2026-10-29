"""Tests for configuration parsing, masking, and validation."""

# [Project-Defined Import from src.config.settings]: Application settings class
from src.config.settings import AppSettings


# [Project-Defined Test Function]: Validates that AppSettings.to_safe_dict masks API keys and database credentials
def test_settings_safe_dict_masks_secrets():
    # [Project-Defined Class Instance: AppSettings]: Instantiate settings with test dummy secrets
    settings = AppSettings(
        gemini_api_key="AIzaSyDummyKey123",
        mysql_password="SuperSecretPassword!",
    )
    # [Project-Defined Method: AppSettings.to_safe_dict]: Export sanitized dict
    safe = settings.to_safe_dict()
    # [Built-in Python: assert]: Ensure neither key nor password are exposed in the dictionary
    assert "AIzaSyDummyKey123" not in str(safe)
    assert "SuperSecretPassword!" not in str(safe)
    assert safe["has_gemini_api_key"] is True
    assert safe["has_mysql_password"] is True


# [Project-Defined Test Function]: Validates that runtime readiness flags missing GEMINI_API_KEY
def test_runtime_readiness_detects_missing_api_key():
    # [Project-Defined Class Instance: AppSettings]: Empty API key
    settings = AppSettings(gemini_api_key="")
    # [Project-Defined Method: AppSettings.validate_runtime_readiness]: Check issues
    issues = settings.validate_runtime_readiness()
    # [Built-in Python: any]: Check that issue list mentions GEMINI_API_KEY
    assert any("GEMINI_API_KEY" in issue for issue in issues)
