"""Client OpenRouter multi-modèle via le SDK openai."""

import time
import json
from openai import OpenAI
from rich.console import Console

console = Console(stderr=True)

_client: OpenAI | None = None
_config: dict | None = None
_verbose: bool = False


def _extract_json(text: str) -> str:
    """Extrait le JSON brut d'une réponse LLM (gère les blocs ```json...```)."""
    if not text:
        return "{}"
    text = text.strip()

    # Cas 1 : bloc markdown ```json ... ```
    if "```" in text:
        import re
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

    # Cas 2 : commence par { ou [ → déjà du JSON brut
    if text.startswith(("{", "[")):
        return text

    # Cas 3 : du texte avant le JSON, trouver le premier { ou [
    for i, c in enumerate(text):
        if c in ("{", "["):
            return text[i:]

    return text


def init(api_key: str, config: dict, verbose: bool = False):
    global _client, _config, _verbose
    _config = config
    _verbose = verbose
    _client = OpenAI(
        base_url=config["openrouter"]["base_url"],
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/linkedin-ghost-writer",
            "X-Title": "LinkedIn Ghost Writer",
        },
    )


def _resolve_model(model_key: str) -> str:
    return _config["openrouter"]["models"][model_key]


def _get_temperature(model_key: str) -> float:
    return _config.get("defaults", {}).get("temperature", {}).get(model_key, 0.7)


def call(
    messages: list[dict],
    model_key: str,
    temperature: float | None = None,
    max_tokens: int = 4096,
) -> str:
    """Appel LLM standard, retourne le texte brut."""
    model = _resolve_model(model_key)
    temp = temperature if temperature is not None else _get_temperature(model_key)

    for attempt in range(3):
        try:
            if _verbose:
                console.print(f"  [dim]LLM → {model} (t={temp})[/dim]")

            response = _client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tokens,
            )

            usage = response.usage
            if _verbose and usage:
                console.print(
                    f"  [dim]Tokens: {usage.prompt_tokens} in → {usage.completion_tokens} out[/dim]"
                )

            return response.choices[0].message.content

        except Exception as e:
            if attempt < 2:
                wait = 2 ** (attempt + 1)
                if _verbose:
                    console.print(f"  [yellow]Retry {attempt + 1}/3 in {wait}s: {e}[/yellow]")
                time.sleep(wait)
            else:
                raise


def call_json(
    messages: list[dict],
    model_key: str,
    temperature: float | None = None,
    max_tokens: int = 4096,
) -> dict | list:
    """Appel LLM avec réponse JSON structurée."""
    model = _resolve_model(model_key)
    temp = temperature if temperature is not None else _get_temperature(model_key)

    for attempt in range(3):
        try:
            if _verbose:
                console.print(f"  [dim]LLM (JSON) → {model} (t={temp})[/dim]")

            response = _client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            usage = response.usage
            if _verbose and usage:
                console.print(
                    f"  [dim]Tokens: {usage.prompt_tokens} in → {usage.completion_tokens} out[/dim]"
                )

            content = response.choices[0].message.content
            return json.loads(_extract_json(content))

        except json.JSONDecodeError:
            if attempt < 2:
                if _verbose:
                    console.print("  [yellow]JSON parse failed, retrying...[/yellow]")
                time.sleep(1)
            else:
                raise

        except Exception as e:
            if attempt < 2:
                wait = 2 ** (attempt + 1)
                if _verbose:
                    console.print(f"  [yellow]Retry {attempt + 1}/3 in {wait}s: {e}[/yellow]")
                time.sleep(wait)
            else:
                raise
