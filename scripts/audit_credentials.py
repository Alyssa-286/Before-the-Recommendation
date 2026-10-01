"""Bounded per-credential capacity audit (no secrets recorded).

For every configured credential variable: list models (auth check), send one
tiny bounded chat request, and record status + rate-limit headers. Shared quota
is detected by interleaving tiny requests across keys of the same provider and
checking whether one key's usage decrements the other's remaining counter.
Writes artifacts/credential_capacity_audit.json.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.runtime_config import load_runtime_environment  # noqa: E402

UA = "before-the-recommendation-research/0.1"
POOLS = {
    "gemini": ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"],
    "mistral": ["MISTRAL_API_KEY", "MISTRAL_API_KEY_2"],
    "groq": ["GROQ_API_KEY", "GROQ_API_KEY_2"],
}
ALL = [name for names in POOLS.values() for name in names]


def _secrets() -> list[str]:
    return [os.environ[n] for n in ALL if os.environ.get(n)]


def _sanitize(text: str) -> str:
    for secret in _secrets():
        text = text.replace(secret, "[REDACTED]")
    return text


def http(method: str, url: str, headers: dict[str, str], body: dict | None = None, timeout: float = 60):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, method=method, headers={"User-Agent": UA, "content-type": "application/json", **headers})
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as resp:
            status, raw, hdrs = resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except HTTPError as exc:
        status, raw, hdrs = exc.code, exc.read(), {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
    except (URLError, TimeoutError) as exc:
        return 0, {"error": _sanitize(type(exc).__name__)}, {}, 0.0
    latency = (time.perf_counter() - started) * 1000
    text = _sanitize(raw.decode("utf-8", errors="replace"))
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {"non_json_preview": text[:300]}
    rl = {k: v for k, v in hdrs.items() if "ratelimit" in k or k in ("retry-after", "x-request-id")}
    return status, payload, rl, round(latency, 1)


def gemini(name: str, model: str) -> dict:
    key = os.environ[name]
    s_list, p_list, _, _ = http("GET", "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", {"x-goog-api-key": key})
    models = sorted(m["name"].removeprefix("models/") for m in p_list.get("models", [])) if s_list == 200 else []
    s, p, rl, lat = http("POST", f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                         {"x-goog-api-key": key},
                         {"contents": [{"parts": [{"text": "Reply with the single word OK."}]}],
                          "generationConfig": {"maxOutputTokens": 8}})
    return {"auth_list_status": s_list, "model_count": len(models), "target_model_listed": model in models,
            "tiny_call_status": s, "usage": p.get("usageMetadata"), "model_version": p.get("modelVersion"),
            "error": p.get("error") if s != 200 else None, "rate_limit_headers": rl, "latency_ms": lat}


def oai_compat(base: str, name: str, model: str, max_key: str = "max_tokens") -> dict:
    key = os.environ[name]
    s_list, p_list, rl_list, _ = http("GET", f"{base}/models", {"Authorization": f"Bearer {key}"})
    models = sorted(m["id"] for m in p_list.get("data", []) if isinstance(m, dict)) if s_list == 200 else []
    s, p, rl, lat = http("POST", f"{base}/chat/completions", {"Authorization": f"Bearer {key}"},
                         {"model": model, "messages": [{"role": "user", "content": "Reply with the single word OK."}], max_key: 8})
    return {"auth_list_status": s_list, "model_count": len(models), "models": models, "target_model_listed": model in models,
            "tiny_call_status": s, "usage": p.get("usage"), "observed_model": p.get("model"),
            "error": p.get("error") if s != 200 else None, "rate_limit_headers": rl, "list_rate_limit_headers": rl_list, "latency_ms": lat}


def remaining(rl: dict, key: str) -> int | None:
    try:
        return int(rl[key])
    except (KeyError, ValueError):
        return None


def sharing_test(call, names: list[str], counter: str) -> dict:
    """Interleave tiny calls a,b,a and compare a remaining-counter sequence."""
    seq = []
    for name in [names[0], names[1], names[0], names[1]]:
        res = call(name)
        seq.append({"key_variable": name, "status": res["tiny_call_status"], counter: remaining(res["rate_limit_headers"], counter)})
        time.sleep(1.5)
    a = [x[counter] for x in seq if x["key_variable"] == names[0]]
    b = [x[counter] for x in seq if x["key_variable"] == names[1]]
    verdict = "undetermined"
    if None not in a + b:
        # Shared org: a's counter drops by >=2 between its calls (b's call consumed shared quota).
        if a[0] - a[1] >= 2 and b[0] - b[1] >= 2:
            verdict = "shared_quota_pool"
        elif a[0] - a[1] == 1 and b[0] - b[1] == 1:
            verdict = "independent_quota_pools"
    return {"counter": counter, "sequence": seq, "verdict": verdict}


def main() -> None:
    load_runtime_environment(names=ALL)
    out = {"artifact_version": "credential-capacity-audit-v1", "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "credential_values_recorded": False, "credentials": {}, "sharing": {}}
    presence = {n: ("SET" if os.environ.get(n) else "NOT SET") for n in ALL}
    out["presence"] = presence
    gem_model = "gemini-3.1-flash-lite"
    for n in POOLS["gemini"]:
        if presence[n] == "SET":
            out["credentials"][n] = {"provider": "google_gemini", **gemini(n, gem_model)}
    mistral_model = "mistral-small-latest"
    for n in POOLS["mistral"]:
        if presence[n] == "SET":
            out["credentials"][n] = {"provider": "mistral", **oai_compat("https://api.mistral.ai/v1", n, mistral_model)}
    for n in POOLS["groq"]:
        if presence[n] == "SET":
            out["credentials"][n] = {"provider": "groq", **oai_compat("https://api.groq.com/openai/v1", n, "openai/gpt-oss-20b", "max_completion_tokens")}
    for c in out["credentials"].values():
        c.pop("models", None) if c.get("provider") == "groq" else None
    # Shared-quota tests where providers expose remaining counters.
    if all(presence[n] == "SET" for n in POOLS["groq"]):
        out["sharing"]["groq"] = sharing_test(lambda n: oai_compat("https://api.groq.com/openai/v1", n, "openai/gpt-oss-20b", "max_completion_tokens"),
                                              POOLS["groq"], "x-ratelimit-remaining-requests")
    if all(presence[n] == "SET" for n in POOLS["mistral"]):
        sample = out["credentials"]["MISTRAL_API_KEY"]["rate_limit_headers"]
        counter = next((k for k in sample if "remaining" in k and "month" in k), next((k for k in sample if "remaining" in k), None))
        if counter:
            out["sharing"]["mistral"] = sharing_test(lambda n: oai_compat("https://api.mistral.ai/v1", n, mistral_model), POOLS["mistral"], counter)
    path = ROOT / "artifacts" / "credential_capacity_audit.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    assert not any(secret in text for secret in _secrets()), "secret leaked into artifact"
    for n, c in out["credentials"].items():
        print(n, c["provider"], "list", c["auth_list_status"], "call", c["tiny_call_status"], "target_listed", c["target_model_listed"],
              "rl", {k: v for k, v in c["rate_limit_headers"].items() if "request-id" not in k}, "err", (json.dumps(c["error"])[:200] if c["error"] else None))
    print(json.dumps(out["sharing"], indent=1))


if __name__ == "__main__":
    main()
