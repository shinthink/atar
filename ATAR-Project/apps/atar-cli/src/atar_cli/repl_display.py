"""ATAR REPL display helpers — additional pure functions extracted from rich_repl.py."""

from __future__ import annotations

# ── Tool icons for display ──

TOOL_ICONS: dict[str, str] = {
    "read_file": "\U0001f4d6",
    "write_file": "\u270d\ufe0f",
    "terminal": "\U0001f4bb",
    "web_fetch": "\U0001f50e",
    "web_search": "\U0001f50d",
    "patch": "\U0001f527",
    "git": "\U0001f500",
    "run_tests": "\u2714\ufe0f",
    "search_files": "\U0001f50e",
    "browser": "\U0001f310",
    "execute_code": "\u2699\ufe0f",
    "cronjob": "\u23f0",
    "delegate_task": "\U0001f465",
    "session_search": "\U0001f50d",
    "session_resume": "\u21a9\ufe0f",
    "load_skill": "\U0001f4e6",
}


def tool_display_icon(name: str) -> str:
    """Get emoji icon for a tool."""
    return TOOL_ICONS.get(name, "\U0001f527")


def tool_display_preview(name: str, args: dict) -> str:
    """Build a short preview string for tool display."""
    if name in ("read_file", "write_file"):
        return args.get("path", str(args))[:60]
    elif name == "terminal":
        return f"$ {args.get('command', '')[:60]}"
    return str(args)[:60]


# ── ATAR ASCII banners ──

COSMIKE_BANNER = [
    "  :::. :::::::::::::::.    :::::::..         :::.      .,-:::::/ .,:::::::::.    :::.::::::::::::",
    "  ;;`;;;;;;;;;;'''';;`;;   ;;;;``;;;;        ;;`;;   ,;;-'````'  ;;;;''''`;;;;,  `;;;;;;;;;;;''''",
    " ,[[ '[[,   [[    ,[[ '[[,  [[[,/[[['       ,[[ '[[, [[[   [[[[[[/[[cccc   [[[[[. '[[     [[",
    "c$$$cc$$$c  $$   c$$$cc$$$c $$$$$$c        c$$$cc$$$c\"$$c.    \"$$ $$\"\"\"\"   $$$ \"Y$c$$     $$",
    " 888   888, 88,   888   888,888b \"88bo,     888   888,`Y8bo,,,o88o888oo,__ 888    Y88     88,",
    " YMM   \"\"`  MMM   YMM   \"\"` MMMM   \"W\"      YMM   \"\"`   `'YMUP\"YMM\"\"\"\"YUMMMMMM     YM     MMM",
]

BRAIN_LOGO = [
    "                                          ",
    "                ####  ####                ",
    "           ####   ##   ##  ####           ",
    "        ###      ##    ###     ###        ",
    "      ###       ##      ##        ##      ",
    "     ##        ##        ##        ###    ",
    "   ###        ##          ##         ##   ",
    "   ##         #            ##         ##  ",
    "  ##         ##             ##        ##  ",
    "  ##        ##      ##       ##        ## ",
    "  #        ##      ####      ##        ## ",
    "  #######    ######    ###### #######*### ",
    "  ##     ##  ######    #####   ##     *#  ",
    "   #*    #                      ##    ##  ",
    "   ##   ##                       ##  ##   ",
    "    #####                         ####    ",
    "      ##                          ##      ",
    "        ###                    ####       ",
    "          ####              ####          ",
    "              ##############              ",
]

BANNER_COLORS = ["primary", "secondary", "accent", "primary", "secondary", "accent"]
TAGLINE = "Clarity in Complexity."


# ── Response text helpers ──

def fallback_response_text(response_text: str, had_tools: bool) -> str | None:
    """Determine response text when model returns empty output.

    Returns the text to display, or None if no response should be shown.
    """
    if response_text.strip():
        return response_text
    if had_tools:
        return "_Work completed — see tool results above._"
    return None


# ── Result line formatting ──

def format_tool_result_line(name: str, args: dict, result: str, elapsed: float, max_lines: int = 10) -> list[str]:
    """Format tool result output for display. Returns list of display lines."""
    lines: list[str] = []
    if name == "terminal":
        preview = args.get("command", "")[:50]
        if result:
            result_lines = result.strip().split("\n")
            if len(result_lines) > max_lines:
                for l in result_lines[:max_lines]:
                    lines.append(f"  │ [dim]{l}[/]")
                lines.append(f"  │ [dim]... {len(result_lines) - max_lines} more lines[/]")
        lines.append(f"  │ 💻 [bold]terminal[/] [dim]{preview} ({elapsed:.1f}s)[/]")
    elif name == "write_file":
        path = args.get("path", "")
        size = len(result) if result else 0
        lines.append(f"  │ ✍️ [bold]write[/] [dim]{path} ({size}B, {elapsed:.1f}s)[/]")
    elif name == "read_file":
        path = args.get("path", "")
        lines.append(f"  │ 📖 [bold]read[/] [dim]{path} ({len(result)} chars, {elapsed:.1f}s)[/]")
    elif name == "patch":
        path = args.get("path", "")
        lines.append(f"  │ 🔧 [bold]patch[/] [dim]{path} ({elapsed:.1f}s)[/]")
    else:
        lines.append(f"  │ [bold]{name}[/] [dim]({elapsed:.1f}s)[/]")
    return lines
