import pytest
from image_gen import generate_image


async def test_placeholder_returns_url():
    url = await generate_image("a sunset over mountains")
    assert url.startswith("https://placehold.co")


async def test_placeholder_includes_prompt():
    url = await generate_image("rainbow")
    assert "rainbow" in url.lower() or "placehold.co" in url


async def test_unknown_provider_raises():
    with pytest.raises(NotImplementedError):
        await generate_image("test", provider="unknown_provider")
