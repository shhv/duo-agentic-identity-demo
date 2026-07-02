"""ANSI colored terminal output helpers for demo presentation."""


class Colors:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"


def banner(agent_name: str, color: str = Colors.CYAN):
    """Print a boxed agent banner."""
    width = 60
    line = "═" * width
    print(f"\n{color}╔{line}╗{Colors.RESET}")
    title = f"  {agent_name}  "
    padding = width - len(title)
    left_pad = padding // 2
    right_pad = padding - left_pad
    print(f"{color}║{' ' * left_pad}{Colors.BOLD}{title}{Colors.RESET}{color}{' ' * right_pad}║{Colors.RESET}")
    print(f"{color}╚{line}╝{Colors.RESET}\n")


def section(title: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}─── {title} ───{Colors.RESET}\n")


def tool_result(tool_name: str, allowed: bool, detail: str = ""):
    """Print a colored tool call result."""
    if allowed:
        icon = f"{Colors.GREEN}✓ ALLOWED{Colors.RESET}"
    else:
        icon = f"{Colors.RED}✗ DENIED{Colors.RESET}"

    print(f"  {icon}  {Colors.BOLD}{tool_name}{Colors.RESET}")
    if detail:
        print(f"         {Colors.DIM}{detail}{Colors.RESET}")


def info(msg: str):
    """Print an info message."""
    print(f"  {Colors.BLUE}ℹ{Colors.RESET}  {msg}")


def success(msg: str):
    """Print a success message."""
    print(f"  {Colors.GREEN}✓{Colors.RESET}  {msg}")


def error(msg: str):
    """Print an error message."""
    print(f"  {Colors.RED}✗{Colors.RESET}  {msg}")


def warn(msg: str):
    """Print a warning message."""
    print(f"  {Colors.YELLOW}⚠{Colors.RESET}  {msg}")


def summary(allowed: int, denied: int):
    """Print final summary box."""
    total = allowed + denied
    width = 40
    print(f"\n{'─' * width}")
    print(f"  Results: {Colors.GREEN}{allowed}/{total} allowed{Colors.RESET}, "
          f"{Colors.RED}{denied}/{total} denied{Colors.RESET}")
    print(f"{'─' * width}\n")
