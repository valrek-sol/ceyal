import datetime as dt
from enum import Enum
import uuid
import json
import shutil
import os
import sys
from pathlib import Path

APP_NAME = "ceyal"

def get_default_db_path():
    if sys.platform.startswith("linux"):
        data_home = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    elif sys.platform == "darwin":
        data_home = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        data_home = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        data_home = Path.home()  # fallback
    
    app_data_dir = Path(data_home) / APP_NAME
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir/"tasks.json"

DB_FILE_PATH_DEFAULT = get_default_db_path()

class TaskStatus(str, Enum):
    PENDING = "pending" 
    ONGOING = "ongoing" 
    PAUSED  = "paused"
    COMPLETED = "completed"

class Task:
    def __init__(self, name, target_time, desc=None, dead_time=None, id=None):
        self.name = name
        if id is None:
            self.id = uuid.uuid4().hex
        else:
            self.id = id
        self.target_time = target_time
        self.desc = desc
        self.dead_time = dead_time
        self.created_time = dt.datetime.now()
        self.start_times = []
        self.pause_times = []
        self.is_complete = False

    @property
    def is_running(self):
        return (len(self.start_times) > len(self.pause_times) and not self.is_complete)

    @property
    def status(self):
        if self.is_complete: return TaskStatus.COMPLETED
        if self.is_running: return TaskStatus.ONGOING
        if not self.start_times: return TaskStatus.PENDING
        return TaskStatus.PAUSED

    def start(self):
        if self.status == TaskStatus.PENDING:
            self.start_times.append(dt.datetime.now())
            print(f"Task '{self.name}' started.")
        elif self.status == TaskStatus.ONGOING:
            print(f"Task '{self.name}' is already running.")
        else:
            print(f"Cannot start {self.status} task. Try 'resume'.")

    def resume(self):
        if self.status == TaskStatus.PAUSED:
            self.start_times.append(dt.datetime.now())
            print(f"Task '{self.name}' resumed.")
        elif self.status == TaskStatus.ONGOING:
            print(f"Task '{self.name}' is already running.")
        else:
            print(f"Cannot resume {self.status} task.")

    def pause(self):
        if self.status == TaskStatus.ONGOING:
            self.pause_times.append(dt.datetime.now())
            print(f"Task '{self.name}' paused.")
        else:
            print(f"Cannot pause {self.status} task.")

    def complete(self):
        if self.status == TaskStatus.ONGOING:
            self.pause_times.append(dt.datetime.now())
        if self.status == TaskStatus.COMPLETED:
            print(f"Task '{self.name}' is already completed.")
            return
        self.is_complete = True
        print(f"Task '{self.name}' completed.")

    @property
    def elapsed_time(self):
        if not self.start_times: return 0.0
        return (dt.datetime.now() - self.start_times[0]).total_seconds()

    @property
    def active_time(self):
        active_t = 0.0
        for start, pause in zip(self.start_times, self.pause_times):
            active_t += (pause - start).total_seconds()
        if self.is_running:
            active_t += (dt.datetime.now() - self.start_times[-1]).total_seconds()
        return active_t

    @property
    def start_time(self):
        return self.start_times[0] if self.start_times else None

    def to_dict(self):
        return {
            "name": self.name, "id": self.id,
            "target_time": self.target_time.isoformat() if self.target_time else None,
            "desc": self.desc,
            "dead_time": self.dead_time.isoformat() if self.dead_time else None,
            "created_time": self.created_time.isoformat(),
            "start_times": [t.isoformat() for t in self.start_times],
            "pause_times": [t.isoformat() for t in self.pause_times],
            "is_complete": self.is_complete
        }

    @classmethod
    def from_dict(cls, data):
        task = cls(
            name=data['name'],
            target_time=dt.datetime.fromisoformat(data['target_time']) if data['target_time'] else None,
            desc=data['desc'],
            dead_time=dt.datetime.fromisoformat(data['dead_time']) if data['dead_time'] else None,
            id=data['id']
        )
        task.created_time = dt.datetime.fromisoformat(data['created_time'])
        task.start_times = [dt.datetime.fromisoformat(t) for t in data['start_times']]
        task.pause_times = [dt.datetime.fromisoformat(t) for t in data['pause_times']]
        task.is_complete = data['is_complete']
        return task

class TaskManager:
    def __init__(self, db_file=DB_FILE_PATH_DEFAULT):
        self.tasks = {}
        self.db_file = db_file

    def __enter__(self):
        self.load_tasks()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.save_tasks()
        if exc_type:
            print(f"Program Crashed due to {exc_value}.")
            return False 
        return True

    def save_tasks(self):
        try:
            backup_path = self.db_file.with_suffix(self.db_file.suffix + ".bak")
            shutil.copy(self.db_file, backup_path)
        except FileNotFoundError:
            pass

        data_write = {tid: t.to_dict() for tid, t in self.tasks.items()}
        with open(self.db_file, 'w') as f:
            json.dump(data_write, f, indent=4)

    def load_tasks(self):
        try:
            with open(self.db_file, 'r') as f:
                data_read = json.load(f)
            self.tasks = {tid: Task.from_dict(t_data) for tid, t_data in data_read.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self.tasks = {}

    def add(self, name, target_time, desc=None, dead_time=None):
        task = Task(name, target_time, desc, dead_time)
        self.tasks[task.id] = task
        print(f"Added Task: {task.name} ({task.id[:6]})")
        return task.id

    def remove(self, task_id):
        if task_id in self.tasks:
            del self.tasks[task_id]
        else:
            raise KeyError(f"Task {task_id} not found")

    def get(self, task_id):
        return self.tasks.get(task_id)

    def list_all(self, show_all=False, filter_status=None):
        print(f"\n{'='*10} CEYAL TASK LIST {'='*10}")
        
        #sorting by created time
        sorted_tasks = sorted(self.tasks.values(), key=lambda x: x.created_time)
        count = 0

        for task in sorted_tasks:
            if filter_status and task.status != filter_status:
                continue
            if not show_all and not filter_status and task.status == TaskStatus.COMPLETED:
                continue

            #color coding ANSI escape codes
            status_color = ""
            if task.status == TaskStatus.ONGOING: status_color = "\033[94m" # Blue
            elif task.status == TaskStatus.COMPLETED: status_color = "\033[92m" # Green
            elif task.status == TaskStatus.PAUSED: status_color = "\033[93m" # Yellow
            reset = "\033[0m"

            print(f"[{status_color}{task.status.value.upper():^9}{reset}] {task.name} (ID: {task.id[:6]})")
            count += 1
        
        if count == 0:
            print("  No tasks found.")
        print("="*37 + "\n")
