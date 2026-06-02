import datetime as dt 
import humanize
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from .custom_types import TaskStatus
from . import theme_parse as theme 

console = Console()

def _parse_time(time_val: str) -> dt.datetime | None:
    #just take string and get datetime object out
    if not time_val: return None
    if isinstance(time_val, dt.datetime): return time_val
    return dt.datetime.fromisoformat(time_val)

def _humanize_deadline(target_time: str, dead_time: str, time_now: dt.datetime) -> str:
    target_dt = _parse_time(target_time)
    dead_dt = _parse_time(dead_time) if dead_time else None
    
    if not target_dt:
        return "-"

    if time_now <= target_dt:
        return humanize.naturaltime(target_dt - time_now)
    
    active_deadline = dead_dt if dead_dt else target_dt

    if active_deadline and time_now <= active_deadline:
        return humanize.naturaltime(active_deadline - time_now)
    
    reference = dead_dt if dead_dt else target_dt
    fatality = theme.get_warning('FATALITY')
    return f"{fatality} {humanize.naturaltime(time_now - reference)}"

def _get_status_icon(status: TaskStatus) -> str:
    icons = {
        TaskStatus.PENDING: theme.get_icon("pending"),
        TaskStatus.ONGOING: theme.get_icon("ongoing"),
        TaskStatus.PAUSED: theme.get_icon("paused"),
        TaskStatus.COMPLETED: theme.get_icon("completed"),
    }
    
    icon = icons.get(status, "?")
    
    if status == TaskStatus.ONGOING and theme.is_blinking():
        return f"[blink]{icon}[/blink]"
        
    return icon

def render_text(message: str):
    console.print(f"[white]{message}[/white]") #really, we need it in the config? nah.

def render_task_action(task, action: str):
    icon = _get_status_icon(task.status)
    console.print(f"{icon} [bold]{action}:[/bold] {task.name} [dim]({task.id[:6]})[/dim]")

def render_list(tasks, time_now=None):
    if not time_now:
        time_now = dt.datetime.now(dt.timezone.utc)

    table = Table(**theme.get_table_kwargs())
    
    table.add_column(theme.get_icon("header_status"), justify="center", width=3)
    table.add_column("ID", width=6)
    table.add_column("Name")
    table.add_column("Deadline", justify="right")

    for task in tasks:
        urgency = task.urgency(time_now)
        color = theme.get_color(urgency.name)
        
        icon = _get_status_icon(task.status)
        warning_sym = theme.get_warning(urgency.name)
        
        name_display = f"{task.name} {warning_sym}".strip()
        deadline_str = _humanize_deadline(task.target_time, task.dead_time, time_now)
        
        row_style = f"{color} strike dim" if task.status == TaskStatus.COMPLETED else color
            
        table.add_row(
            icon, 
            task.id[:6], 
            name_display, 
            deadline_str, 
            style=row_style
        )
        
    console.print(table)

def render_task_detail(task, verbosity: int, time_now=None):
    if not time_now:
        time_now = dt.datetime.now(dt.timezone.utc)

    urgency = task.urgency(time_now)
    color = theme.get_color(urgency.name)
    status_icon = _get_status_icon(task.status)
    warning_sym = theme.get_warning(urgency.name)
    
    # Title construction
    title_text = f"{status_icon} {task.name} {warning_sym}".strip()
    
    details = []
    
    # Level 0 (No verbosity)
    details.append(f"ID: {task.id[:6]}")
    if task.desc: details.append(f"Desc: {task.desc}")
    details.append(f"Deadline: {_humanize_deadline(task.target_time, task.dead_time, time_now)}")
    details.append(f"Priority: {task.priority}")
    
    # Level 1 (-v)
    if verbosity >= 1:
        details[0] = f"ID: {task.id}" # Expand ID
        details.append(f"Status: {task.status.value.upper()}")
        details.append(f"Active: {task.active_time:.1f}s")
        details.append(f"Elapsed: {task.elapsed_time:.1f}s")
        
        tt = _parse_time(task.target_time)
        tst = _parse_time(task.target_start_time)
        details.append(f"Target: {tt.strftime('%Y-%m-%d %H:%M %Z') if tt else 'None'}")
        details.append(f"Start Target: {tst.strftime('%Y-%m-%d %H:%M %Z') if tst else 'None'}")

    # Level 2 (-vv) -> RAW values
    if verbosity >= 2:
        details.append("--- RAW DATA ---")
        details.append(f"Time Ratio: {task.time_ratio(time_now):.4f}")
        details.append(f"Urgency: {urgency.name}")
        details.append(f"Created: {task.created_time}")
        details.append(f"Last Pause: {task.last_pause_time}")
        details.append(f"Started: {task.start_time}")

    # Render Panel
    panel_content = "\n".join(details)
    panel = Panel(
        panel_content, 
        title=title_text, 
        border_style=color,
        expand=False
    )
    console.print(panel)
