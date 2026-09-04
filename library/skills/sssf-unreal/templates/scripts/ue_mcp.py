import urllib.request
import urllib.error
import json
import os
import re
import sys
import time
import argparse

MCP_URL = f"http://127.0.0.1:{os.environ.get('UNREAL_MCP_PORT', '8000')}/mcp"
TOKEN_PATH = "Saved/MCP/capability-token"
BLOCKLIST_REGEX = re.compile(r"(?i)\b(quit|exit|rmdir|remove|git\s+reset|git\s+clean)\b")

def get_capability_token() -> str:
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r") as f:
            return f.read().strip()
    return ""

def validate_command_safety(command_str: str):
    if BLOCKLIST_REGEX.search(command_str):
        raise ValueError(f"Command '{command_str}' blocked by security regex filter.")

class UnrealMCPClient:
    def __init__(self, url: str = MCP_URL, timeout: float = 30.0):
        self.url = url
        self.timeout = timeout
        self.session_id = None
        self.token = get_capability_token()
        self._initialize_session()

    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self.token:
            headers["X-MCP-Capability-Token"] = self.token
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _initialize_session(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "sssf-cli", "version": "1.0"}
            }
        }
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"), headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                self.session_id = response.headers.get("Mcp-Session-Id")
        except (urllib.error.URLError, OSError) as e:
            # Handle initialization errors gracefully, maybe log and continue without session_id
            print(f"Warning: Could not initialize MCP session. {e}", file=sys.stderr)

    def _send_request(self, method: str, params: dict = None) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": params or {}
        }
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"), headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as e:
            return {
                "status": "error",
                "error_code": "SERVER_UNREACHABLE",
                "message": f"Unreal Editor MCP server not reachable at {self.url}. Ensure UE5 is running. Details: {e}"
            }

    def ping(self) -> dict:
        return self._send_request("ping") # Assuming a 'ping' method exists on the MCP

    def _call_standard(self, tool_name: str, arguments: dict = None) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments or {}}
        }
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"), headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            return {
                "status": "error",
                "error_code": "SERVER_UNREACHABLE",
                "message": f"Unreal Editor MCP server not reachable at {self.url}. Ensure UE5 is running. Details: {e}"
            }

    def list_toolsets(self) -> dict:
        return self._call_standard("list_toolsets")

    def describe_toolset(self, toolset_name: str) -> dict:
        return self._call_standard("describe_toolset", {"toolset_name": toolset_name})

    def call_tool(self, toolset_name: str, tool_name: str, arguments: dict = None) -> dict:
        validate_command_safety(tool_name)
        return self._call_standard("call_tool", {
            "toolset_name": toolset_name,
            "tool_name": tool_name,
            "arguments": arguments or {}
        })


def extract_tool_text(resp: dict) -> str:
    """Extract the text payload of a tools/call response. Returns '' for error envelopes."""
    if not isinstance(resp, dict) or "result" not in resp:
        return ""
    result = resp["result"]
    if not isinstance(result, dict):
        return ""
    content = result.get("content")
    if not isinstance(content, list) or not content:
        return ""
    first = content[0]
    if isinstance(first, dict):
        return first.get("text", "")
    return ""

def main():
    parser = argparse.ArgumentParser(description="Unreal Editor MCP CLI client.")
    parser.add_argument("command", choices=["ping", "list", "describe", "search", "call", "run"], help="MCP command to execute.")
    parser.add_argument("toolset_tool", nargs="?", help="Toolset.Tool for 'describe', 'call', and 'run' commands.")
    parser.add_argument("--args", help='JSON string of arguments for the command (e.g., \'{"param1": "value1"}\').')
    parser.add_argument("--args-file", help="Path to a JSON file containing arguments, or '-' for stdin.")

    args = parser.parse_args()

    mcp_params = {}
    if args.args:
        mcp_params = json.loads(args.args)
    elif args.args_file:
        if args.args_file == "-":
            mcp_params = json.load(sys.stdin)
        else:
            with open(args.args_file, "r") as f:
                mcp_params = json.load(f)

    client = UnrealMCPClient()

    result = {}

    if args.command == "ping":
        result = client.ping()
    elif args.command == "list":
        result = client.list_toolsets()
    elif args.command == "describe":
        if not args.toolset_tool:
            parser.error("describe command requires a toolset name argument (e.g. ActorTools).")
        result = client.describe_toolset(args.toolset_tool)
    elif args.command == "search":
        # Search logic would go here, possibly filtering list_toolsets output
        print("Search command not fully implemented yet. Listing all toolsets.")
        result = client.list_toolsets()
    elif args.command in ("call", "run"):
        if not args.toolset_tool:
            parser.error("call/run command requires Toolset.Tool argument (e.g. editor_toolset.toolsets.asset.AssetTools.exists).")
        parts = args.toolset_tool.rsplit(".", 1)
        if len(parts) == 2:
            toolset_name, tool_name = parts
        else:
            parser.error("'call' and 'run' commands require Toolset.Tool format (e.g., 'editor_toolset.toolsets.asset.AssetTools.exists').")

        result = client.call_tool(toolset_name, tool_name, mcp_params)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
