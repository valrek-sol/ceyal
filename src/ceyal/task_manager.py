import datetime as dt
from enum import Enum
import uuid
from .database import DatabaseManager
from .custom_types import TaskRow

class TaskStatus(str, Enum):
    PENDING = "pending" 
    ONGOING = "ongoing" 
    PAUSED  = "paused"
    COMPLETED = "completed"

class Task:
    def __init__(self, id=None, name="0", desc=None,
             target_start_time=None,
             target_time=None,
             created_time=None,
             dead_time=None,
             is_complete=False,
             priority=1,
             events=None):
    
        self.id = id or uuid.uuid4().hex
        self.name = name
        self.desc = desc
        self.target_start_time = target_start_time or dt.datetime.now(dt.timezone.utc)
        self.target_time = target_time or (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1))
        self.created_time = created_time or dt.datetime.now(dt.timezone.utc)
        self.dead_time = dead_time
        self.is_complete = is_complete
        self.priority = priority
        self._events = events if events is not None else []

    def to_row(self) -> TaskRow :
        return TaskRow(
                id  = self.id,
                name = self.name,
                description = self.desc,
                target_start_time = self.target_start_time,
                target_time = self.target_time,
                created_time = self.created_time,
                dead_time = self.dead_time,
                is_complete = self.is_complete,
                priority = self.priority
                )

    @classmethod
    def from_row(cls, row: TaskRow, events = None):
        return cls(
                id = row.id,
                name = row.name,
                desc = row.description,
                target_start_time = row.target_start_time,
                target_time = row.target_time, created_time = row.created_time,
                dead_time = row.dead_time,
                is_complete = row.is_complete,
                priority = row.priority,
                events = events
                )

    @property
    def is_running(self):
        if not self._events or self.is_complete :
            return False
        else:
            return self._events[-1].event_type in ('start','resume') 

    @property
    def status(self):
        if self.is_complete: return TaskStatus.COMPLETED
        if self.is_running: return TaskStatus.ONGOING
        if not self._events: return TaskStatus.PENDING
        return TaskStatus.PAUSED

    def start(self):
        if self.status != TaskStatus.PENDING:
            raise ValueError(f"Cannot start a {self.status.value} task | {self.id}  {self.name}")
        return ('start', dt.datetime.now(dt.timezone.utc) )

    def resume(self):
        if self.status != TaskStatus.PAUSED:
            raise ValueError(f"Cannot resume a {self.status.value} task | {self.id}  {self.name}")
        return ('resume', dt.datetime.now(dt.timezone.utc) )

    def pause(self):
        if self.status != TaskStatus.ONGOING:
            raise ValueError(f"Cannot pause a {self.status.value} task | {self.id}  {self.name}")
        return ('pause', dt.datetime.now(dt.timezone.utc) )

    def complete(self):
        if self.status == TaskStatus.COMPLETED:
            raise ValueError(f"Cannot complete a {self.status.value} task | {self.id}  {self.name}")
        self.is_complete = True
        return ('complete', dt.datetime.now(dt.timezone.utc) )

    @property
    def elapsed_time(self):
        '''
        Time interval "elapsed" from the very start till "now" or completed timestamp.
        Includes paused time intervals.
        '''

        if not self._events: return 0.0

        if self.is_complete:
            return (dt.datetime.fromisoformat((self._events[-1].timestamp))- dt.datetime.fromisoformat((self._events[0].timestamp))).total_seconds()
        else:
            return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat((self._events[0].timestamp))).total_seconds()

    @property
    def active_time(self):
        '''
        Time interval "active" from start to "now",
        excluding paused time intervals.
        '''

        if not self._events: return 0.0

        active_t = 0.0
        open_interval = None

        for e in self._events:
            if e.event_type in ('start','resume'):
                open_interval = dt.datetime.fromisoformat(e.timestamp)
            elif e.event_type in ('pause','complete'):
                if open_interval:
                    active_t += (dt.datetime.fromisoformat(e.timestamp) - open_interval).total_seconds()
                    open_interval = None
        if open_interval:
            active_t += (dt.datetime.now(dt.timezone.utc) - open_interval).total_seconds()

        return active_t

    # start_time and last_pause_time return a ISO format aware datetime string
    @property
    def start_time(self):
        return self._events[0].timestamp if (self._events and self._events[0].event_type in ('start')) else None

    @property
    def last_pause_time(self):
        return self._events[-1].timestamp if (self._events and self._events[-1].event_type in ('pause','complete')) else None


class TaskManager:
    def __init__(self):
        self.db = DatabaseManager()

    def __enter__(self):
        self.db.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.db.__exit__(exc_type, exc_value, traceback)

    def _resolve_task(self, partial_id):
        task = self.db.fetch_task_by_partial_id(partial_id)
        task_events = self.db.fetch_task_events([(task.id,)])
        return Task.from_row(task,task_events)


    def add(self, name, target_start_time, target_time, desc=None,
            dead_time=None, priority=1):
        task = Task(name=name,target_start_time=target_start_time,
                    target_time=target_time, desc=desc, dead_time=dead_time,
                    is_complete=False, priority=priority)
        self.db.create_task([task.to_row()])
        return task

    def remove_by_id(self, partial_id):
        task = self._resolve_task(partial_id)
        self.db.delete_task_by_id([(task.id,)])
        return task

    def get_task(self, partial_id):
        task = self._resolve_task(partial_id)
        return task 

    def list_all_tasks(self, rows = None):
        return self.db.fetch_all_tasks(rows)

    def start_task(self, partial_id):
        task = self._resolve_task(partial_id)
        event_type , timestamp = task.start()
        self.db.task_event_entry([(task.id,)],event_type, timestamp.isoformat())
        return task

    def pause_task(self, partial_id):
        task = self._resolve_task(partial_id)
        event_type , timestamp = task.pause()
        self.db.task_event_entry([(task.id,)],event_type, timestamp.isoformat())
        return task

    def resume_task(self, partial_id):
        task = self._resolve_task(partial_id)
        event_type , timestamp = task.resume()
        self.db.task_event_entry([(task.id,)],event_type, timestamp.isoformat())
        return task

    def complete_task(self, partial_id):
        task = self._resolve_task(partial_id)
        event_type , timestamp = task.complete()
        self.db.task_event_entry([(task.id,)],event_type, timestamp.isoformat())
        self.db.modify_task([(task.id,)],[("is_complete",True)])
        return task
