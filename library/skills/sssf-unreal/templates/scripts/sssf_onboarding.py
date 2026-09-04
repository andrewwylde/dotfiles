import os
import sys
import socket
import sqlite3
import subprocess
from time import sleep

# Try importing Rich for premium CLI interface, fallback to standard prints
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    class SimpleConsole:
        def print(self, msg, *args, **kwargs):
            # Strip simple rich formatting tags
            msg = str(msg).replace("[green]", "").replace("[/green]", "")
            msg = msg.replace("[bold]", "").replace("[/bold]", "")
            msg = msg.replace("[red]", "").replace("[/red]", "")
            msg = msg.replace("[yellow]", "").replace("[/yellow]", "")
            msg = msg.replace("[cyan]", "").replace("[/cyan]", "")
            print(msg)
    console = SimpleConsole()

def check_tcp_port(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def run_preflight_checks():
    checks = []
    
    # 1. Check .env and API Key
    has_env = os.path.exists(".env")
    has_key = False
    if has_env:
        with open(".env") as f:
            for line in f:
                if "OPENROUTER_API_KEY" in line and not line.strip().startswith("#"):
                    has_key = len(line.split("=", 1)[1].strip()) > 10
                    break
    checks.append(("OpenRouter API Key (.env)", has_key, "Configured" if has_key else "Missing key in .env"))
    
    # 2. Check UCP TCP Bridge (Port 9876)
    ucp_active = check_tcp_port("127.0.0.1", 9876)
    checks.append(("Unreal UCP TCP Bridge (Port 9876)", ucp_active, "Running" if ucp_active else "Offline (Start UE Editor)"))
    
    # 3. Check Unreal MCP Server (Port 8000)
    mcp_active = check_tcp_port("127.0.0.1", 8000)
    checks.append(("Unreal MCP Server (Port 8000)", mcp_active, "Active" if mcp_active else "Offline (Start UE Editor)"))
    
    # 4. Check sssf.db
    db_exists = os.path.exists("adws/adw_data/sssf.db")
    checks.append(("SSSF SQLite Database (sssf.db)", db_exists, "Found" if db_exists else "Not yet created"))

    return checks

def display_welcome():
    title = "[bold cyan]SSSF (Super Simple Software Factory) Onboarding[/bold cyan]"
    body = (
        "Welcome! SSSF is our developer harness for automated coding. "
        "It coordinates planning, code-writing, test executions, and code reviews.\n\n"
        "This onboarding flow will check your environment, explain how to invoke workflows, "
        "and help you execute your first SSSF agent run."
    )
    if HAS_RICH:
        console.print(Panel(body, title=title, border_style="cyan", padding=(1, 2)))
    else:
        console.print(f"=== {title} ===")
        console.print(body)
        console.print("-" * 50)

def display_preflight(checks):
    title = "[bold yellow]Preflight Checklist[/bold yellow]"
    if HAS_RICH:
        table = Table(title="SSSF Service Status Checklist", show_header=True, header_style="bold magenta")
        table.add_column("Service/Check", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Message", style="dim")
        
        for name, passed, msg in checks:
            status = "[bold green]PASS[/bold green]" if passed else "[bold red]FAIL[/bold red]"
            table.add_row(name, status, msg)
            
        console.print(table)
    else:
        console.print(f"=== {title} ===")
        for name, passed, msg in checks:
            status = "PASS" if passed else "FAIL"
            console.print(f" - {name}: [{status}] {msg}")
        console.print("-" * 50)

def display_tutorial():
    title = "[bold green]SSSF Workflow Guide[/bold green]"
    if HAS_RICH:
        table = Table(title="Available Developer Workflows", show_header=True, header_style="bold cyan")
        table.add_column("Workflow Shortcut", style="bold green")
        table.add_column("Command Line Syntax", style="yellow")
        table.add_column("What it does", style="dim")
        
        table.add_row(
            "just prompt",
            'just prompt "<instructions>" [--agent <name>]',
            "Queries a single agent (scout, builder, reviewer) directly."
        )
        table.add_row(
            "just scout",
            'just scout "<question about code>"',
            "Explores codebase structure, finds symbols, and does read-only recon."
        )
        table.add_row(
            "just plan",
            'just plan "<feature description>"',
            "Turns natural language request into a specification file in specs/"
        )
        table.add_row(
            "just plan-build",
            'just plan-build "<feature description>"',
            "Generates a spec, writes/modifies C++/Python files, and commits them to git."
        )
        table.add_row(
            "just sdlc",
            'just sdlc "<feature description>"',
            "Executes complete loop: Spec -> Build -> Test Suite -> Commit on pass."
        )
        table.add_row(
            "just obs",
            "just obs",
            "Starts trace visualization web UI (port 4601)."
        )
        console.print(table)
    else:
        console.print(f"=== {title} ===")
        console.print(" - just prompt: Run a single prompt through an agent.")
        console.print(" - just scout: Ask read-only questions about the codebase.")
        console.print(" - just plan: Generate an implementation specification file.")
        console.print(" - just plan-build: Generate spec and implement code changes.")
        console.print(" - just sdlc: Plan, build, run quality tests, and commit on pass.")
        console.print(" - just obs: Start trace visualizer dashboard.")
        console.print("-" * 50)

def run_scout_demo():
    prompt = "what is the current status of the floppy arms milestone?"
    cmd = [
        "uv", "run", "adws/adw_prompt.py", 
        "--config", "adws/adw_sssf_config/sssf.config.yaml", 
        "--agent", "scout", 
        prompt
    ]
    
    console.print(Panel(
        f"We will now launch a read-only [bold green]scout[/bold green] agent run:\n"
        f"[yellow]Command:[/yellow] `{' '.join(cmd)}`\n\n"
        f"This will query the LLM to inspect our local ROADMAP.md and report back.",
        title="[bold green]Running Scout Demo[/bold green]"
    ))
    
    if not Confirm.ask("Do you want to start the demo run?"):
        console.print("[yellow]Demo skipped.[/yellow]")
        return
        
    console.print("\n[cyan][+][/cyan] Running scout agent workflow. Please wait...")
    
    # Run the process and capture output
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1
        )
        
        # Real-time print output
        for line in process.stdout:
            print(line.strip())
            
        process.wait()
        
        if process.returncode == 0:
            console.print("\n[bold green]✓ Demo completed successfully![/bold green]")
        else:
            console.print(f"\n[bold red]✗ Demo process exited with code {process.returncode}[/bold red]")
            
    except Exception as e:
        console.print(f"\n[bold red]✗ Error running demo: {e}[/bold red]")

def main():
    display_welcome()
    sleep(1.0)
    
    # Run and display preflight status
    checks = run_preflight_checks()
    display_preflight(checks)
    sleep(1.0)
    
    # Check if we should warn about offline Unreal Editor
    mcp_passed = checks[2][1]
    if not mcp_passed:
        console.print(
            "[bold red]⚠ Warning:[/bold red] The Unreal Editor is not running or port 8000/9876 is closed. "
            "Please open the project in Unreal Editor to utilize full live-in-editor automation capabilities.\n"
        )
    
    display_tutorial()
    sleep(1.0)
    
    # Offer live demonstration if OpenRouter key is set
    key_passed = checks[0][1]
    if key_passed:
        run_scout_demo()
    else:
        console.print("\n[yellow]Skipping live demo since OPENROUTER_API_KEY is not configured or invalid.[/yellow]")
        
    console.print("\n[bold cyan]=== Next Steps ===[/bold cyan]")
    console.print("1. [bold green]just obs[/bold green]: Open the visualizer dashboard to review previous execution traces.")
    console.print("2. [bold green]just scout \"your question\"[/bold green]: Query the codebase.")
    console.print("3. Read [bold]docs/SSSF_USER_MANUAL.md[/bold] for full details.")
    console.print("\nEnjoy using the Super Simple Software Factory!\n")

if __name__ == "__main__":
    main()
