from collections import namedtuple
from enum import Enum, auto

class TaskStatus(str, Enum):
    PENDING = "pending" 
    ONGOING = "ongoing" 
    PAUSED  = "paused"
    COMPLETED = "completed"

class TaskUrgency(int, Enum):
    #auto increment auto()...
    NONE = 0 
    RELAX = auto() 
    LOW  = auto()
    MED = auto()
    HIGH = auto()
    CRITICAL = auto()
    CRITICAL_GRACE = auto()
    FATALITY = auto()

task_parameters = ["id","name","description","target_start_time",
                   "target_time","created_time","dead_time",
                   "is_complete","priority"]
TaskRow = namedtuple("TaskRow", task_parameters)

timestamp_parameters = ["event_id","task_id","event_type","timestamp"]
TimestampRow = namedtuple("TimestampRow", timestamp_parameters)

task_relations_parameters = ["super_task_id","sub_task_id"]
TaskRelationsRow = namedtuple("TaskRelationsRow",task_relations_parameters)
