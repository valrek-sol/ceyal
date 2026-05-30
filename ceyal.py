#!/usr/bin/env python3

import argparse
import sys
import datetime as dt
import dateparser
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from task_manager import TaskManager, TaskStatus

console = Console()

AVAILABLE_PARAMETERS = ["desc", "created", "target", "dead", "elapsed",
                        "active", "start", "pause"]

def parse_datetime(date_str):
    #i hope the dateparser is light enough ... why reinvent the wheel moment
    if not date_str:
        return None
    try:
        return dateparser.parse(date_str,settings={'TO_TIMEZONE': 'UTC','RETURN_AS_TIMEZONE_AWARE': True}) 
    except ValueError as e:
        console.print(f"[bold red]Error: {e} [/bold red] Could not parse date '{date_str}'") 

def handle_add(args, tm):
    t_time = parse_datetime(args.target)
    d_time = parse_datetime(args.dead)
    ts_time = parse_datetime(args.target_start_time)
        
    task = tm.add(name=args.name, target_start_time=ts_time, target_time=t_time,
                  desc=args.desc, dead_time=d_time, priority=args.priority)
    
    console.print(f"[bold green] Task Added:[/bold green] {task.name}")
    console.print(f"  [dim]ID:[/dim] {task.id}")

def handle_list(args, tm):
    #whole thing is just inefficient, just query according to event_type from db itself, 
    #it works for now
    tasks = tm.list_all_tasks()
    
    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

    table = Table(title="list of tasks", title_style="bold magenta", border_style="dim")
    
    table.add_column("ID", style="dim", width=7)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Name", style="bold white")
    table.add_column("Active Time", justify="right", style="cyan")
    
    count = 0
    for row in tasks:
        task = tm.get_task(row.id)
        
        if args.pending and task.status != TaskStatus.PENDING:
            continue
        if args.ongoing and task.status != TaskStatus.ONGOING:
            continue
        if args.paused and task.status != TaskStatus.PAUSED:
            continue
        if args.completed and task.status != TaskStatus.COMPLETED:
            continue
        if (not args.all or not args.completed) and task.status == TaskStatus.COMPLETED:
            continue
            
        status_str = task.status.value
        if task.status == TaskStatus.ONGOING:
            state = f"[bold blue]{status_str}[/bold blue]"
        elif task.status == TaskStatus.COMPLETED:
            state = f"[bold green]{status_str}[/bold green]"
        elif task.status == TaskStatus.PENDING:
            state = f"[bold red]{status_str}[/bold red]"
        else:
            state = f"[bold yellow]{status_str}[/bold yellow]"
            
        if task.active_time > 0:
            active_mins = task.active_time / 60
            active_t_str = f"{active_mins:.1f} m"
        else:
            active_t_str = "-"
            
        table.add_row(task.id[:6], state, task.name, active_t_str)
        count += 1
        
    if count == 0:
        console.print("[yellow]No tasks match your filters.[/yellow]")
    else:
        console.print(table)

def handle_remove(args, tm):
    if args.all:
        confirm = console.input("[bold red]Are you sure you want to DELETE ALL tasks? (y/n): [/bold red]")
        if confirm.lower() == 'y':
            all_rows = tm.list_all_tasks()
            for row in all_rows:
                tm.remove_by_id(row.id)
            console.print("[bold green]All tasks cleared.[/bold green]")
    else:
        if not args.id:
            console.print("[bold red]Error:[/bold red] Provide an ID or use --all")
            return
        try:
            task = tm.remove_by_id(args.id)
            console.print(f"[bold green]Removed task:[/bold green] {task.name}")
        except (KeyError, ValueError) as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

def handle_state_change(args, tm):
    try:
        if args.command == 'start':
            task = tm.start_task(args.id)
            console.print(f"[bold blue]▶ Started:[/bold blue] {task.name} ({task.id[:6]})")
        elif args.command == 'pause':
            task = tm.pause_task(args.id)
            console.print(f"[bold yellow]⏸ Paused:[/bold yellow] {task.name} ({task.id[:6]})")
        elif args.command == 'resume':
            task = tm.resume_task(args.id)
            console.print(f"[bold blue]▶ Resumed:[/bold blue] {task.name} ({task.id[:6]})")
        elif args.command == 'complete':
            task = tm.complete_task(args.id)
            console.print(f"[bold green]✔ Completed:[/bold green] {task.name} ({task.id[:6]})")
    except Exception as e:
         console.print(f"[bold red]Error:[/bold red] {e}")

def handle_get(args, tm):
    try:
        task = tm.get_task(args.id)
        
        details = [
            f"[dim]ID:[/dim] {task.id}",
            f"[dim]Status:[/dim] [bold]{task.status.value.upper()}[/bold]",
            f"[dim]Created:[/dim] {task.created_time}",
            f"[dim]Target:[/dim] {task.target_time}",
            f"[dim]Dead:[/dim] {task.dead_time or 'None'}",
            f"[dim]Active Time:[/dim] {task.active_time:.1f} secs",
            f"[dim]Elapsed Time:[/dim] {task.elapsed_time:.1f} secs"
        ]
        
        if task.desc:
            details.insert(2, f"[dim]Description:[/dim] {task.desc}")
            
        panel = Panel("\n".join(details), title=f"[bold cyan]{task.name}[/bold cyan]", border_style="cyan", expand=False)
        console.print(panel)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


def main():
    parser = argparse.ArgumentParser(
            prog = 'ceyal',
            description = " ++ ++ Ceyal : Task Management Engine ++ ++ "
            )
    subparsers = parser.add_subparsers(
            dest = 'command',
            required = True,
            title = "Commands",
            help = "action to perform"
            )

    add_p = subparsers.add_parser('add', help = "Create a New Task")
    add_p.add_argument('name', type = str, help = "Task Name")
    add_p.add_argument('-t','--target', type = str, help = "Target Time")
    add_p.add_argument('-s','--target_start_time', type = str, help = "Target Start Time (suggested start time)")
    add_p.add_argument('-d','--desc', type = str, help = "Task Description")
    add_p.add_argument('-p','--priority',type = int, help = "Assign Priority (natural numbers 1 to N)") 
    add_p.add_argument('--dead', type = str, help = "Dead Time")
    add_p.set_defaults(func=handle_add)   

    list_p = subparsers.add_parser('list', help = "List Tasks")
    list_p.add_argument('-e','--pending', action = 'store_true', help = "List all pending Tasks")
    list_p.add_argument('-o','--ongoing', action = 'store_true', help = "List all ongoing Tasks")
    list_p.add_argument('-p','--paused', action = 'store_true', help = "List all paused Tasks")
    list_p.add_argument('-c','--completed', action = 'store_true', help = "List all completed Tasks")
    list_p.add_argument('-a','--all', action = 'store_true', help = "List all Tasks")
    list_p.set_defaults(func=handle_list)   

    remove_p = subparsers.add_parser('remove', help = "Remove a Task")
    remove_p.add_argument('id', nargs='?', type = str, help = "Remove a task with ID")
    remove_p.add_argument('-a','--all', action = 'store_true', help = "Remove all Tasks")
    remove_p.set_defaults(func=handle_remove)   
    
    start_p = subparsers.add_parser('start', help = "Start an existing Task")
    start_p.add_argument('id', type = str, help = "Task ID")
    start_p.set_defaults(func=handle_state_change)

    pause_p = subparsers.add_parser('pause', help = "Pause an existing Task")
    pause_p.add_argument('id', type = str, help = "Task ID")
    pause_p.set_defaults(func=handle_state_change)

    resume_p = subparsers.add_parser('resume', help = "Resume an existing Task")
    resume_p.add_argument('id', type = str, help = "Task ID")
    resume_p.set_defaults(func=handle_state_change)

    complete_p = subparsers.add_parser('complete', help = "Complete an existing Task")
    complete_p.add_argument('id', type = str, help = "Task ID")
    complete_p.set_defaults(func=handle_state_change)

    get_p = subparsers.add_parser('get', help = "View a Task")
    get_p.add_argument('id', type = str, help = "Task ID")
    get_p.add_argument('parameters', type = str, nargs = '?', choices = AVAILABLE_PARAMETERS , help = "get specific details about a task")
    get_p.add_argument('-v','--verbose', action = 'count', help = "View details")
    get_p.set_defaults(func=handle_get)
    
    args = parser.parse_args()

    with TaskManager() as tm:
        if hasattr(args, 'func'):
            args.func(args, tm)

if __name__ == "__main__":
    main()
