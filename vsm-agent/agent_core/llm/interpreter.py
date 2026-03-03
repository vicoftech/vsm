"""
LLM-based prompt interpreter for Agent Core.

Uses AWS Bedrock (Claude Haiku) to:
- Clasificar la intención del usuario
- Resolver skill_id y mcp_target
- Construir parámetros estructurados para el MCP

El modelo debe devolver SIEMPRE un JSON válido, por ejemplo:

{
  "intent": "create_ticket",
  "skill_id": "jira_create_issue",
  "mcp_target": "jira",
  "parameters": {
    "projectKey": "VSM",
    "issueType": "Story"
  },
  "confidence": 0.93,
  "fallback_message": "No pude determinar la acción..."
}

Si Bedrock no está disponible o la respuesta es inválida, este módulo
lanza `LLMInterpreterError` y el caller puede hacer fallback al
heurístico.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict
import logging

from agent_core.config.settings import AgentCoreSettings
from agent_core.models.agent_context import AgentContext

try:
    import boto3  # type: ignore

    _BOTO3_AVAILABLE = True
except ImportError:  # pragma: no cover - local dev sin AWS SDK
    boto3 = None  # type: ignore
    _BOTO3_AVAILABLE = False


class LLMInterpreterError(Exception):
    """Raised when the LLM interpreter cannot produce a valid result."""


@dataclass
class InterpreterResult:
    intent: str
    skill_id: str | None
    mcp_target: str | None
    parameters: Dict[str, Any]
    confidence: float
    fallback_message: str | None


def _build_system_prompt() -> str:
    return (
        "Sos el módulo de interpretación de un agente que trabaja con Jira y Confluence.\n"
        "Tu tarea es leer el mensaje del usuario (en español o inglés) y devolver SOLO un JSON "
        "con esta forma:\n\n"
        "{\n"
        '  \"intent\": \"...\",\n'
        '  \"skill_id\": \"...\",\n'
        '  \"mcp_target\": \"jira\" | \"confluence\" | null,\n'
        "  \"parameters\": { ... },\n"
        "  \"confidence\": 0.0-1.0,\n"
        "  \"fallback_message\": \"...\" (opcional)\n"
        "}\n\n"
        "No expliques nada, no agregues texto fuera del JSON.\n"
        "Si no estás seguro, usá intent \"unknown\" y poné una fallback_message amigable.\n"
    )


_logger = logging.getLogger(__name__)


def _parse_llm_json(text: str) -> Dict[str, Any]:
    """
    Intenta parsear el JSON devuelto por el modelo de forma tolerante.

    - Primero intenta `json.loads` directo.
    - Si falla con JSONDecodeError, intenta extraer el primer objeto `{ ... }`
      dentro del texto (para el caso en que el modelo agregue texto extra
      antes o después del JSON).
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: buscar el primer bloque JSON bien balanceado en el texto.
        n = len(text)
        for i, ch in enumerate(text):
            if ch != "{":
                continue
            depth = 0
            for j in range(i, n):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[i : j + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            # Probar siguiente bloque
                            break
        # Si tampoco se encuentra un bloque JSON claro, re-lanzar el error original
        raise


def interpret_prompt(
    ctx: AgentContext,
    *,
    settings: AgentCoreSettings,
) -> InterpreterResult:
    """
    Call Bedrock to interpret the user's prompt.

    Soporta dos familias de modelos:
    - Titan Text (`amazon.titan-text-*`)
    - Claude (Anthropic) para compatibilidad futura

    Raises:
        LLMInterpreterError if the model is not available or response is invalid.
    """
    if not _BOTO3_AVAILABLE:
        raise LLMInterpreterError("boto3 is not available in this environment")

    bedrock = boto3.client(
        "bedrock-runtime", region_name=settings.llm.bedrock_region
    )

    model_id = settings.llm.interpreter_model

    # Prompt combinado (system + user) para modelos tipo Titan
    combined_prompt = _build_system_prompt() + "\n\nUsuario:\n" + ctx.prompt + "\n\nJSON:"

    # === Titan Text: amazon.titan-* (text generation) ===
    #
    # Incluimos aquí las familias históricas `amazon.titan-text-*` y el
    # modelo actual `amazon.titan-tg1-large`, que comparten la misma
    # interfaz de generación de texto basada en `inputText`.
    if model_id.startswith("amazon.titan-text") or model_id.startswith(
        "amazon.titan-tg1"
    ):
        body = {
            "inputText": combined_prompt,
            "textGenerationConfig": {
                "maxTokenCount": 512,
                "temperature": 0.1,
                "topP": 0.9,
            },
        }

        try:
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(body).encode("utf-8"),
            )
            raw = response.get("body").read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - red/AWS failures
            raise LLMInterpreterError(
                f"Bedrock Titan invocation failed: {exc}"
            ) from exc

        try:
            payload = json.loads(raw)
            # Titan devuelve results[0].outputText
            results = payload.get("results") or []
            if not results:
                raise ValueError("No results from Titan model")
            text = results[0].get("outputText", "")
            data = _parse_llm_json(text)
        except Exception as exc:
            raise LLMInterpreterError(f"Could not parse Titan JSON: {exc}") from exc

    elif model_id.startswith("mistral."):
        # === Mistral (e.g. mistral.ministral-3-8b-instruct) ===
        #
        # Los modelos instruct de Mistral en Bedrock usan un esquema tipo:
        # {
        #   "prompt": "...",
        #   "max_tokens": 512,
        #   "temperature": 0.1,
        #   "top_p": 0.9
        # }
        body = {
            "prompt": combined_prompt,
            "max_tokens": 512,
            "temperature": 0.1,
            "top_p": 0.9,
        }

        try:
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(body).encode("utf-8"),
            )
            raw = response.get("body").read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - red/AWS failures
            raise LLMInterpreterError(
                f"Bedrock Mistral invocation failed: {exc}"
            ) from exc

        try:
            payload = json.loads(raw)
            # Mistral devuelve typically `outputs[0].text`
            outputs = payload.get("outputs") or []
            if not outputs:
                raise ValueError("No outputs from Mistral model")
            text = outputs[0].get("text", "")
            data = _parse_llm_json(text)
        except Exception as exc:
            raise LLMInterpreterError(f"Could not parse Mistral JSON: {exc}") from exc

    elif model_id.startswith("meta.llama3"):
        # === Llama 3 (Meta) usando invoke_model directo ===
        #
        # Usamos el esquema típico documentado para Llama en Bedrock:
        # {
        #   "prompt": "...",
        #   "temperature": 0.5,
        #   "top_p": 0.9,
        #   "max_gen_len": 512
        # }
        body = {
            "prompt": combined_prompt,
            "temperature": 0.5,
            "top_p": 0.9,
            "max_gen_len": 512,
        }

        try:
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(body).encode("utf-8"),
                contentType="application/json",
                accept="application/json",
            )
            raw = response.get("body").read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - red/AWS failures
            raise LLMInterpreterError(
                f"Bedrock Llama invocation failed: {exc}"
            ) from exc

        try:
            payload = json.loads(raw)
            text: str | None = None

            if isinstance(payload, dict):
                # Intentar varios campos comunes
                for key in ("generation", "output_text", "generated_text", "text"):
                    val = payload.get(key)
                    if isinstance(val, str):
                        text = val
                        break

                # Algunos modelos usan `outputs[0].text`
                if text is None and "outputs" in payload:
                    outputs = payload.get("outputs") or []
                    if outputs and isinstance(outputs[0], dict):
                        cand = outputs[0].get("text") or outputs[0].get("output_text")
                        if isinstance(cand, str):
                            text = cand

            # Si no encontramos un campo específico, asumimos que el propio raw
            # ya es el JSON de intent.
            if text is None:
                text = raw

            # Loguear salida cruda para debugging (recortada)
            _logger.info(
                "Raw Llama3 output for trace %s: %s",
                ctx.trace_id,
                (text[:1000] if isinstance(text, str) else "<non-str>"),
            )

            data = _parse_llm_json(text)
        except Exception as exc:
            raise LLMInterpreterError(f"Could not parse Llama JSON: {exc}") from exc

    else:
        # === Claude / otros modelos con interfaz de mensajes (Anthropic) ===
        #
        # Nota importante: la API de mensajes de Anthropic en Bedrock espera
        # el prompt del sistema en el campo top-level `system`, NO como un
        # mensaje más con role "system" dentro de `messages`. El error que
        # vimos en CloudWatch era:
        #   messages: Unexpected role "system". The Messages API accepts a
        #   top-level `system` parameter, not "system" as an input message role.
        #
        # Por eso enviamos:
        #   - `system`: lista con un solo bloque de texto
        #   - `messages`: solo el mensaje del usuario (role "user")

        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": ctx.prompt,
                }
            ],
        }

        body = {
            "system": [
                {
                    "type": "text",
                    "text": _build_system_prompt(),
                }
            ],
            "messages": [user_message],
            "max_tokens": 512,
            "temperature": 0.1,
            "top_p": 0.9,
            # Versión recomendada por la API de Anthropic en Bedrock.
            "anthropic_version": "bedrock-2023-05-31",
        }

        try:
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(body).encode("utf-8"),
            )
            raw = response.get("body").read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - red/AWS failures
            raise LLMInterpreterError(
                f"Bedrock Claude invocation failed: {exc}"
            ) from exc

        try:
            payload = json.loads(raw)
            if isinstance(payload, dict) and "content" in payload:
                text = "".join(
                    part.get("text", "")
                    for part in payload["content"]
                    if isinstance(part, dict)
                )
            else:
                text = raw

            data = _parse_llm_json(text)
        except Exception as exc:
            raise LLMInterpreterError(f"Could not parse Claude JSON: {exc}") from exc

    intent = str(data.get("intent") or "unknown")
    skill_id = data.get("skill_id")
    mcp_target = data.get("mcp_target")
    parameters = data.get("parameters") or {}
    confidence = float(data.get("confidence") or 0.0)
    fallback_message = data.get("fallback_message")

    return InterpreterResult(
        intent=intent,
        skill_id=skill_id,
        mcp_target=mcp_target,
        parameters=parameters,
        confidence=confidence,
        fallback_message=fallback_message,
    )


