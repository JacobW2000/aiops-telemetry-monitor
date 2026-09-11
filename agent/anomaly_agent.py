import asyncio
import json
import websockets
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_ollama import ChatOllama

OPENAI_API_KEY = None
MCP_SSE_URL = "http://localhost:8001/sse"

async def evaluate_anomaly(metric_data: dict):
    print(f"\n[ALERT] Anomaly Detected: CPU at {metric_data['cpu_percent']}%!")
    print("[AGENT] Connecting to FastMCP Server for Diagnostics...")

    async with sse_client(MCP_SSE_URL) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()

            # Retrieve tools directly from MCP Server
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"[AGENT] Available MCP Tools: {tool_names}")

            # Execute diagnostic step
            proc_diag = await session.call_tool("inspect_top_processes", {"limit": 5})
            load_diag = await session.call_tool("get_system_load", {})

            # Formulate Incident Analysis using LLM
            llm = ChatOllama(model="llama3.2", api_key=OPENAI_API_KEY)
            prompt = (
                f"You are an automated Site Reliability Engineer (SRE).\n"
                f"A system anomaly occurred with metrics: {metric_data}\n\n"
                f"System Load Diagnostic:\n{load_diag.content[0].text}\n\n"
                f"Top Running Processes:\n{proc_diag.content[0].text}\n\n"
                f"Provide a short root-cause summary and actionable recommendation."
            )

            response = await llm.ainvoke(prompt)
            print("\n=== SRE INCIDENT REPORT ===")
            print(response.content)
            print("===========================\n")

async def listen_telemetry():
    uri = "ws://localhost:8000/ws/telemetry"
    print("Agent listening to real-time telemetry stream...")

    async with websockets.connect(uri) as websocket:
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)

            # Trigger diagnostic agent loop on threshold breach
            if data.get("cpu_percent", 0) > 85.0:
                await evaluate_anomaly(data)
                await asyncio.sleep(10) # Cooldown period

if __name__ == "__main__":
    asyncio.run(listen_telemetry())