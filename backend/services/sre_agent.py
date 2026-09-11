import json
import requests

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "llama3"


def analyze_telemetry_with_ollama(cpu: float, memory: float, disk: float, proc_name: str, proc_cpu: float) -> dict:
    prompt = f"""
    You are an autonomous SRE (Site Reliability Engineering) AI agent monitoring a high-performance system.
    Analyze the following anomalous system metrics and generate an incident report.

    Current Telemetry:
    - CPU Usage: {cpu}%
    - Memory Usage: {memory}%
    - Disk Usage: {disk}%
    - Top Resource-Consuming Process: {proc_name} (utilizing {proc_cpu}% CPU)

    You MUST respond with a valid JSON object matching this exact schema, with no extra text or markdown code blocks outside the JSON:
    {{
      "severity": "CRITICAL" or "WARNING",
      "summary": "Short concise summary of the issue",
      "analysis": "Brief technical root-cause analysis explaining why this is problematic",
      "recommended_action": "Actionable command or step to remediate the issue"
    }}
    """

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2  # Low temperature for deterministic, structured operational responses
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return json.loads(result.get("response", "{}"))
    except Exception as e:
        print(f"Ollama connection error: {e}")

    # Fallback response if Ollama is unreachable
    return {
        "severity": "WARNING",
        "summary": f"High Resource Consumption Detected (CPU: {cpu}%)",
        "analysis": f"Process {proc_name} is consuming heavy system resources.",
        "recommended_action": "Inspect process execution or scale container limits."
    }