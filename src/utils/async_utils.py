from PyQt5.QtCore import QThread, pyqtSignal
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import time

class AsyncWorker(QThread):
    """Worker genérico para tareas asíncronas."""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self._is_running = True

    def run(self):
        try:
            self.task_func(*self.args, **self.kwargs)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._is_running = False

    def stop(self):
        self._is_running = False
        self.wait()

class AsyncProcessor:
    """Clase para manejar procesamiento asíncrono."""
    def __init__(self, max_workers=None):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.loop = asyncio.new_event_loop()
        self.thread = None

    def start(self):
        """Inicia el loop de eventos en un thread separado."""
        if self.thread is None:
            def run_loop():
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()

            self.thread = threading.Thread(target=run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Detiene el procesador asíncrono."""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(timeout=1.0)
        self.executor.shutdown(wait=False)

    async def run_in_executor(self, func, *args):
        """Ejecuta una función en el executor."""
        return await self.loop.run_in_executor(self.executor, func, *args)

    def run_async(self, coro):
        """Ejecuta una corutina en el loop de eventos."""
        if self.loop and self.thread and self.thread.is_alive():
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future
        else:
            raise RuntimeError("AsyncProcessor no está iniciado")

class ProcessManager:
    """Administrador de procesos para tareas pesadas."""
    def __init__(self):
        self.tasks = {}
        self.processor = AsyncProcessor()
        self.processor.start()

    def add_task(self, name, task_func, *args, **kwargs):
        """Agrega una tarea para ejecución asíncrona."""
        if name in self.tasks:
            return False

        worker = AsyncWorker(task_func, *args, **kwargs)
        self.tasks[name] = worker
        worker.finished.connect(lambda: self._cleanup_task(name))
        worker.start()
        return True

    def _cleanup_task(self, name):
        """Limpia los recursos de una tarea terminada."""
        if name in self.tasks:
            worker = self.tasks[name]
            if worker.isFinished():
                worker.deleteLater()
                del self.tasks[name]

    def stop_all(self):
        """Detiene todas las tareas activas."""
        for name, worker in list(self.tasks.items()):
            worker.stop()
            self._cleanup_task(name)
        self.processor.stop()

    def is_task_running(self, name):
        """Verifica si una tarea está en ejecución."""
        return name in self.tasks and self.tasks[name]._is_running

class AsyncTimer:
    """Temporizador asíncrono para operaciones periódicas."""
    def __init__(self, interval, callback, *args, **kwargs):
        self.interval = interval
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self._running = False
        self._task = None

    async def _run(self):
        while self._running:
            try:
                await asyncio.sleep(self.interval)
                if self._running:
                    self.callback(*self.args, **self.kwargs)
            except Exception as e:
                print(f"Error en AsyncTimer: {str(e)}")

    def start(self):
        """Inicia el temporizador."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run())

    def stop(self):
        """Detiene el temporizador."""
        self._running = False
        if self._task:
            self._task.cancel() 