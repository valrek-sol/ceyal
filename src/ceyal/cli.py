#!/usr/bin/env python3

import datetime as dt
import argparse
import dateparser

from .task_manager import TaskManager, TaskStatus
from . import render_cli

AVAILABLE_PARAMETERS = ["desc", "created", "target", "dead", "elapsed",
                        "active", "start", "pause"]

def parse_datetime(date_str):
    if not date_str:
        return None
    try:
        return dateparser.parse(date_str, settings={'TO_TIMEZONE': 'UTC','RETURN_AS_TIMEZONE_AWARE': True}) 
    except ValueError as e:
        render_cli.render_text(f"Error: {e} | Could not parse date '{date_str}'") 

def handle_add(args, tm):
    t_time = parse_datetime(args.target)
    d_time = parse_datetime(args.dead)
    ts_time = parse_datetime(args.target_start_time)
        
    task = tm.add(name=args.name, target_start_time=ts_time, target_time=t_time,
                  desc=args.desc, dead_time=d_time, priority=args.priority)
    
    render_cli.render_task_action(task, "Added")

def handle_list(args, tm):
    tasks_rows = tm.list_all_tasks()
    
    if not tasks_rows:
        render_cli.render_text("No tasks found.")
        return

    time_now = dt.datetime.now(dt.timezone.utc)
    filtered_tasks = []
    
    for row in tasks_rows:
        task = tm.get_task(row.id)
        
        # Apply filters
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
            
        filtered_tasks.append(task)
        
    if not filtered_tasks:
        render_cli.render_text("No tasks match your filters.")
    else:
        render_cli.render_list(filtered_tasks,time_now)

def handle_remove(args, tm):
    if args.all:
        # Using render_cli's console to maintain formatting consistency
        confirm = render_cli.console.input("[bold red]Are you sure you want to DELETE ALL tasks? (y/n): [/bold red]")
        if confirm.lower() == 'y':
            all_rows = tm.list_all_tasks()
            for row in all_rows:
                tm.remove_by_id(row.id)
            render_cli.render_text("All tasks cleared.")
    else:
        if not args.id:
            render_cli.render_text("Error: Provide an ID or use --all")
            return
        try:
            task = tm.remove_by_id(args.id)
            render_cli.render_text(f"Removed task: {task.name} ({task.id[:6]})")
        except (KeyError, ValueError) as e:
            render_cli.render_text(f"Error: {e}")

def handle_state_change(args, tm):
    try:
        if args.command == 'start':
            task = tm.start_task(args.id)
            render_cli.render_task_action(task, "Started")
        elif args.command == 'pause':
            task = tm.pause_task(args.id)
            render_cli.render_task_action(task, "Paused")
        elif args.command == 'resume':
            task = tm.resume_task(args.id)
            render_cli.render_task_action(task, "Resumed")
        elif args.command == 'complete':
            task = tm.complete_task(args.id)
            render_cli.render_task_action(task, "Completed")
    except Exception as e:
         render_cli.render_text(f"Error: {e}")

def handle_get(args, tm):
    try:
        task = tm.get_task(args.id)
        v_level = args.verbose if args.verbose else 0
        render_cli.render_task_detail(task, verbosity=v_level)
    except Exception as e:
        render_cli.render_text(f"Error: {e}")

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
