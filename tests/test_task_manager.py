import time
import threading
from task_manager import TaskManager

def test_task_manager_execution():
    manager = TaskManager(max_concurrent=2)
    result = []
    
    def dummy_task():
        result.append(1)
        
    manager.submit_task(dummy_task)
    
    # Wait for execution
    time.sleep(0.1)
    
    assert result == [1]
    manager.shutdown()

def test_task_manager_tracking():
    manager = TaskManager(max_concurrent=2)
    
    event = threading.Event()
    
    def blocking_task():
        event.wait()
        
    manager.submit_task(blocking_task)
    time.sleep(0.1)
    
    # Check that task is active
    with manager._tasks_lock:
        assert manager._pending_count == 0
        assert len(manager._active_tasks) == 1
        
    event.set()
    time.sleep(0.1)
    
    # Check that task has finished
    with manager._tasks_lock:
        assert manager._pending_count == 0
        assert len(manager._active_tasks) == 0
        
    manager.shutdown()
