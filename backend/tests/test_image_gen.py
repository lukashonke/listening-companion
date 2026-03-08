import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from image_gen import (
    generate_image,
    DEFAULT_OPENAI_IMAGE_MODEL,
    DEFAULT_GEMINI_IMAGE_MODEL,
    _LEGACY_OPENAI_MODELS,
)


# ── Placeholder provider ─────────────────────────────────────────────────────

async def test_placeholder_returns_url():
    url = await generate_image("a sunset over mountains")
    assert url.startswith("https://placehold.co")


async def test_placeholder_includes_prompt():
    url = await generate_image("rainbow")
    assert "rainbow" in url.lower() or "placehold.co" in url


async def test_unknown_provider_raises():
    with pytest.raises(NotImplementedError):
        await generate_image("test", provider="unknown_provider")


# ── Default model constants ──────────────────────────────────────────────────

def test_default_openai_model():
    assert DEFAULT_OPENAI_IMAGE_MODEL == "gpt-image-1"


def test_default_gemini_model():
    assert DEFAULT_GEMINI_IMAGE_MODEL == "gemini-2.5-flash-image"


def test_legacy_models_include_dalle():
    assert "dall-e-2" in _LEGACY_OPENAI_MODELS
    assert "dall-e-3" in _LEGACY_OPENAI_MODELS
    assert "gpt-image-1" not in _LEGACY_OPENAI_MODELS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_settings(**overrides):
    s = MagicMock()
    s.openai_api_key = overrides.get("openai_api_key", "sk-test-key")
    s.google_api_key = overrides.get("google_api_key", "test-google-key")
    return s


def _mock_httpx_client(response):
    """Create a mock AsyncClient that returns the given response on .post()."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post.return_value = response
    return mock_client


def _openai_response(b64="aW1hZ2VkYXRh", url=None):
    item = {}
    if b64:
        item["b64_json"] = b64
    if url:
        item["url"] = url
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"data": [item]}
    return resp


def _gemini_response():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [
                    {"text": "Here's your image"},
                    {"inlineData": {"mimeType": "image/png", "data": "aW1hZ2VkYXRh"}}
                ]
            }
        }]
    }
    return resp


def _imagen_response():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "predictions": [{"bytesBase64Encoded": "aW1hZ2VkYXRh", "mimeType": "image/png"}]
    }
    return resp


# ── OpenAI provider ──────────────────────────────────────────────────────────

@patch("image_gen.httpx.AsyncClient")
async def test_openai_default_model_no_response_format(mock_client_class):
    """gpt-image-1 should NOT send response_format."""
    client = _mock_httpx_client(_openai_response())
    mock_client_class.return_value = client

    with patch("config.settings", _make_settings()):
        url = await generate_image("test prompt", provider="openai")

    assert url.startswith("data:image/png;base64,")
    payload = client.post.call_args[1]["json"]
    assert payload["model"] == "gpt-image-1"
    assert "response_format" not in payload


@patch("image_gen.httpx.AsyncClient")
async def test_openai_custom_model(mock_client_class):
    client = _mock_httpx_client(_openai_response())
    mock_client_class.return_value = client

    with patch("config.settings", _make_settings()):
        await generate_image("test", provider="openai", model="gpt-image-1-mini")

    payload = client.post.call_args[1]["json"]
    assert payload["model"] == "gpt-image-1-mini"
    assert "response_format" not in payload


@patch("image_gen.httpx.AsyncClient")
async def test_openai_dalle3_uses_response_format(mock_client_class):
    """dall-e-3 should use response_format (legacy API)."""
    client = _mock_httpx_client(_openai_response())
    mock_client_class.return_value = client

    with patch("config.settings", _make_settings()):
        await generate_image("test", provider="openai", model="dall-e-3")

    payload = client.post.call_args[1]["json"]
    assert payload["model"] == "dall-e-3"
    assert payload["response_format"] == "b64_json"


@patch("image_gen.httpx.AsyncClient")
async def test_openai_dalle2_uses_response_format(mock_client_class):
    """dall-e-2 should use response_format (legacy API)."""
    client = _mock_httpx_client(_openai_response())
    mock_client_class.return_value = client

    with patch("config.settings", _make_settings()):
        await generate_image("test", provider="openai", model="dall-e-2")

    payload = client.post.call_args[1]["json"]
    assert payload["model"] == "dall-e-2"
    assert payload["response_format"] == "b64_json"


async def test_openai_no_key_raises():
    with patch("config.settings", _make_settings(openai_api_key="")):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            await generate_image("test", provider="openai")


@patch("image_gen.httpx.AsyncClient")
async def test_openai_url_fallback(mock_client_class):
    """If no b64_json, should fall back to url field."""
    client = _mock_httpx_client(_openai_response(b64=None, url="https://example.com/img.png"))
    mock_client_class.return_value = client

    with patch("config.settings", _make_settings()):
        url = await generate_image("test", provider="openai")

    assert url == "https://example.com/img.png"


# ── Gemini provider ──────────────────────────────────────────────────────────

@patch("image_gen.httpx.AsyncClient")
async def test_gemini_default_model(mock_client_class):
    client = _mock_httpx_client(_gemini_response())
    mock_client_class.return_value = client

    with patch("config.settings", _make_settings()):
        url = await generate_image("test", provider="gemini")

    assert url.startswith("data:image/png;base64,")
    call_url = client.post.call_args[0][0]
    assert "gemini-2.5-flash-image" in call_url
    assert ":generateContent" in call_url


@patch("image_gen.httpx.AsyncClient")
async def test_gemini_custom_model(mock_client_class):
    client = _mock_httpx_client(_gemini_response())
    mock_client_class.return_value = client

    with patch("config.settings", _make_settings()):
        await generate_image("test", provider="gemini", model="nano-banana-pro-preview")

    call_url = client.post.call_args[0][0]
    assert "nano-banana-pro-preview" in call_url


@patch("image_gen.httpx.AsyncClient")
async def test_gemini_imagen_uses_predict(mock_client_class):
    """Imagen models should use :predict endpoint."""
    client = _mock_httpx_client(_imagen_response())
    mock_client_class.return_value = client

    with patch("config.settings", _make_settings()):
        url = await generate_image("test", provider="gemini", model="imagen-4.0-generate-001")

    assert url.startswith("data:image/png;base64,")
    call_url = client.post.call_args[0][0]
    assert ":predict" in call_url
    assert "imagen-4.0-generate-001" in call_url


@patch("image_gen.httpx.AsyncClient")
async def test_gemini_imagen_fast(mock_client_class):
    client = _mock_httpx_client(_imagen_response())
    mock_client_class.return_value = client

    with patch("config.settings", _make_settings()):
        url = await generate_image("test", provider="gemini", model="imagen-4.0-fast-generate-001")

    call_url = client.post.call_args[0][0]
    assert "imagen-4.0-fast-generate-001" in call_url


async def test_gemini_no_key_raises():
    with patch("config.settings", _make_settings(google_api_key="")):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            await generate_image("test", provider="gemini")


# ── Model passthrough in image_tool ───────────────────────────────────────────

def test_image_tool_passes_model():
    """build_image_tool should accept and store model parameter."""
    from tools.image_tool import build_image_tool

    tool = build_image_tool("openai", AsyncMock(), model="gpt-image-1.5")
    import inspect
    sig = inspect.signature(tool)
    assert "prompt" in sig.parameters
    assert "style" in sig.parameters


def test_image_tool_default_model_empty():
    """build_image_tool with no model should default to empty string."""
    from tools.image_tool import build_image_tool

    tool = build_image_tool("placeholder", AsyncMock())
    assert tool is not None
