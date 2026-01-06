#!/usr/bin/env python3

import argparse
import sys
import datetime as dt
from task_manager import TaskManager, TaskStatus

def parse_datetime(datetime_str):
    if not datetime_str:
        return None
    try:
        return dt.datetime.fromisoformat(datetime_str)
    except ValueError:
        try:
            return dt.datetime.strptime(datetime_str, "%Y-%m-%d")
        except ValueError:
            print(f"Error: Could not parse date '{datetime_str}'. Use 'YYYY-MM-DDTHH:mm:ss.sssZ' or ISO 8601 format.")
            sys.exit(1)

def find_task_by_partial(tm, partial_id):
    matches = [tid for tid in tm.tasks if tid.startswith(partial_id)]
    
    if len(matches) == 0:
        print(f"Error: No task found starting with '{partial_id}'")
        sys.exit(1)
    elif len(matches) > 1:
        print(f"Error: Ambiguous ID '{partial_id}'. Matches multiple tasks.")
        sys.exit(1)
    
    return tm.get(matches[0])

def handle_add(args, tm):
    t_time = parse_datetime(args.target)
    d_time = parse_datetime(args.dead)
    # If no target provided, default to tomorrow
    if not t_time:
        t_time = dt.datetime.now() + dt.timedelta(days=1)
        
    tm.add(args.name, target_time=t_time, desc=args.desc, dead_time=d_time)

def handle_list(args, tm):
    if args.ongoing:
        tm.list_all(filter_status=TaskStatus.ONGOING)
    else:
        tm.list_all(show_all=args.all)

def handle_remove(args, tm):
    if args.all:
        confirm = input("Are you sure you want to DELETE ALL tasks? (y/n): ")
        if confirm.lower() == 'y':
            all_ids = list(tm.tasks.keys())
            for tid in all_ids:
                tm.remove(tid)
            print("All tasks cleared.")
    else:
        if not args.id:
            print("Error: Provide an ID or use --all")
            return
        task = find_task_by_partial(tm, args.id)
        tm.remove(task.id)
        print(f"Removed task: {task.name}")

def handle_state_change(args, tm):
    task = find_task_by_partial(tm, args.id)
    
    if args.command == 'start':
        task.start()
    elif args.command == 'pause':
        task.pause()
    elif args.command == 'resume':
        task.resume()
    elif args.command == 'complete':
        task.complete()

def handle_get(args, tm):
    task = find_task_by_partial(tm, args.id)
    print(f"\n{'='*10} TASK DETAILS {'='*10}")
    print(f"Name:    {task.name}")
    print(f"ID:      {task.id}")
    print(f"Status:  {task.status.value.upper()}")
    
    if args.verbose and args.verbose > 0:
        print(f"Desc:    {task.desc}")
        print(f"Created: {task.created_time}")
        print(f"Target:  {task.target_time}")
        print(f"Active:  {task.active_time:.2f} sec")
    print("="*34 + "\n")


def main():
    parser = argparse.ArgumentParser(
            prog = 'ceyal',
            description = " ++ ++ A task manager application ++ ++ "
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
    add_p.add_argument('-d','--desc', type = str, help = "Task Description")
    add_p.add_argument('--dead', type = str, help = "Dead Time")
    add_p.set_defaults(func=handle_add)   

    list_p = subparsers.add_parser('list', help = "List Tasks")
    list_p.add_argument('-o','--ongoing', action = 'store_true', help = "List all ongoing Tasks")
    list_p.add_argument('-a','--all', action = 'store_true', help = "List all Tasks")
    list_p.set_defaults(func=handle_list)   

    remove_p = subparsers.add_parser('remove', help = "Remove a Task")
    remove_p.add_argument('id', nargs='?', type = str, help = "Remove a task with ID") # Made optional for -a case
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
    get_p.add_argument('-v','--verbose', action = 'count', help = "View details")
    get_p.set_defaults(func=handle_get)
    
    args = parser.parse_args()

    with TaskManager() as tm:
        if hasattr(args, 'func'):
            args.func(args, tm)

if __name__ == "__main__":
    main()
