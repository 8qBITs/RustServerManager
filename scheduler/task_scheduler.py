"""
Background task scheduler for automation like periodic update checks and auto-updates.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from utils.logger import log
from config.schema import AutomationConfig


class TaskScheduler:
    """
    Manages scheduled background tasks using APScheduler.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.last_run_times: Dict[str, Optional[datetime]] = {}
        self.next_run_times: Dict[str, Optional[datetime]] = {}
        self.task_status: Dict[str, Dict[str, Any]] = {}

    def schedule_update_check(
        self,
        callback: Callable,
        interval_minutes: int = 60,
        job_id: str = "rust_update_check",
    ) -> bool:
        """
        Schedule periodic Rust server update checks.
        """
        try:
            # Remove existing job if present
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass

            self.scheduler.add_job(
                func=self._wrapped_callback(callback, job_id),
                trigger=IntervalTrigger(minutes=interval_minutes),
                id=job_id,
                name=f"Rust Update Check (every {interval_minutes} min)",
                replace_existing=True,
            )
            
            log.info(f"Scheduled '{job_id}' to run every {interval_minutes} minutes")
            return True
        except Exception as e:
            log.error(f"Failed to schedule update check: {e}")
            return False

    def schedule_oxide_update_check(
        self,
        callback: Callable,
        interval_minutes: int = 60,
        job_id: str = "oxide_update_check",
    ) -> bool:
        """
        Schedule periodic Oxide update checks.
        """
        try:
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass

            self.scheduler.add_job(
                func=self._wrapped_callback(callback, job_id),
                trigger=IntervalTrigger(minutes=interval_minutes),
                id=job_id,
                name=f"Oxide Update Check (every {interval_minutes} min)",
                replace_existing=True,
            )
            
            log.info(f"Scheduled '{job_id}' to run every {interval_minutes} minutes")
            return True
        except Exception as e:
            log.error(f"Failed to schedule oxide update check: {e}")
            return False

    def schedule_auto_update(
        self,
        callback: Callable,
        interval_minutes: int = 120,
        job_id: str = "auto_update",
    ) -> bool:
        """
        Schedule periodic automatic updates.
        """
        try:
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass

            self.scheduler.add_job(
                func=self._wrapped_callback(callback, job_id),
                trigger=IntervalTrigger(minutes=interval_minutes),
                id=job_id,
                name=f"Auto Update (every {interval_minutes} min)",
                replace_existing=True,
            )
            
            log.info(f"Scheduled '{job_id}' to run every {interval_minutes} minutes")
            return True
        except Exception as e:
            log.error(f"Failed to schedule auto update: {e}")
            return False

    def schedule_custom_task(
        self,
        callback: Callable,
        job_id: str,
        name: str,
        trigger_type: str = "interval",
        interval_minutes: int = 60,
        daily_time: str = "03:00",
    ) -> bool:
        """Schedule a custom task with interval or daily trigger."""
        try:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass

            if trigger_type == "daily":
                hour, minute = self._parse_daily_time(daily_time)
                trigger = CronTrigger(hour=hour, minute=minute)
                trigger_desc = f"daily at {hour:02d}:{minute:02d}"
            else:
                trigger = IntervalTrigger(minutes=max(1, interval_minutes))
                trigger_desc = f"every {max(1, interval_minutes)} minute(s)"

            self.scheduler.add_job(
                func=self._wrapped_callback(callback, job_id),
                trigger=trigger,
                id=job_id,
                name=name,
                replace_existing=True,
            )

            log.info(f"Scheduled custom task '{job_id}' ({name}) {trigger_desc}")
            return True
        except Exception as e:
            log.error(f"Failed to schedule custom task '{job_id}': {e}")
            return False

    def unschedule_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.
        """
        try:
            self.scheduler.remove_job(job_id)
            log.info(f"Unscheduled job: {job_id}")
            return True
        except Exception as e:
            log.error(f"Failed to unschedule '{job_id}': {e}")
            return False

    def get_scheduled_jobs(self) -> list:
        """
        Get list of currently scheduled jobs.
        """
        return self.scheduler.get_jobs()

    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific job.
        """
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                return None

            return {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "last_run_time": self.last_run_times.get(job_id),
                "status": self.task_status.get(job_id, {}),
            }
        except Exception as e:
            log.error(f"Error getting job info: {e}")
            return None

    def pause_scheduler(self) -> None:
        """
        Pause all scheduled tasks.
        """
        try:
            self.scheduler.pause()
            log.info("Scheduler paused")
        except Exception as e:
            log.error(f"Failed to pause scheduler: {e}")

    def resume_scheduler(self) -> None:
        """
        Resume all scheduled tasks.
        """
        try:
            self.scheduler.resume()
            log.info("Scheduler resumed")
        except Exception as e:
            log.error(f"Failed to resume scheduler: {e}")

    def shutdown(self) -> None:
        """
        Shutdown the scheduler.
        """
        try:
            self.scheduler.shutdown()
            log.info("Scheduler shutdown")
        except Exception as e:
            log.error(f"Error shutting down scheduler: {e}")

    def _wrapped_callback(self, callback: Callable, job_id: str) -> Callable:
        """
        Wrap a callback to track execution times and handle errors.
        """
        def wrapper():
            try:
                self.last_run_times[job_id] = datetime.now()
                self.task_status[job_id] = {"status": "running", "error": None}
                
                result = callback()
                
                self.task_status[job_id] = {"status": "completed", "error": None, "result": result}
                log.info(f"Job '{job_id}' completed successfully")
            except Exception as e:
                self.task_status[job_id] = {"status": "failed", "error": str(e)}
                log.error(f"Job '{job_id}' failed: {e}")
        
        return wrapper

    def _parse_daily_time(self, daily_time: str) -> tuple[int, int]:
        """Parse HH:MM daily time into hour/minute tuple."""
        try:
            hour_text, minute_text = daily_time.split(":", maxsplit=1)
            hour = max(0, min(23, int(hour_text)))
            minute = max(0, min(59, int(minute_text)))
            return hour, minute
        except Exception:
            return 3, 0
