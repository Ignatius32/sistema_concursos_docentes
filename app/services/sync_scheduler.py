"""
Scheduled synchronization service for Keycloak-Persona sync.

This service can be used to run periodic synchronization tasks.
"""

import logging
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import Flask

from app.services.keycloak_persona_sync import get_sync_service

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Scheduler for automatic Keycloak-Persona synchronization."""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.is_running = False
        self.scheduler_thread = None
        self.last_sync_results = {}
        self.sync_history = []
        
    def init_app(self, app: Flask):
        """Initialize scheduler with Flask app."""
        self.app = app
        
        # Configure scheduler based on app config
        sync_interval = app.config.get('KEYCLOAK_SYNC_INTERVAL_HOURS', 24)
        if sync_interval > 0:
            self.schedule_periodic_sync(hours=sync_interval)
            logger.info(f"Scheduled periodic sync every {sync_interval} hours")
    
    def schedule_periodic_sync(self, hours: int = 24):
        """Schedule periodic full synchronization."""
        schedule.every(hours).hours.do(self._run_scheduled_sync)
        logger.info(f"Scheduled sync every {hours} hours")
    
    def schedule_daily_sync(self, time_str: str = "02:00"):
        """Schedule daily synchronization at specific time."""
        schedule.every().day.at(time_str).do(self._run_scheduled_sync)
        logger.info(f"Scheduled daily sync at {time_str}")
    
    def schedule_weekly_sync(self, day: str = "monday", time_str: str = "02:00"):
        """Schedule weekly synchronization."""
        getattr(schedule.every(), day.lower()).at(time_str).do(self._run_scheduled_sync)
        logger.info(f"Scheduled weekly sync on {day} at {time_str}")
    
    def _run_scheduled_sync(self):
        """Execute scheduled synchronization with app context."""
        if not self.app:
            logger.error("Flask app not initialized for scheduled sync")
            return
        
        with self.app.app_context():
            try:
                logger.info("Starting scheduled synchronization")
                
                sync_service = get_sync_service()
                if not sync_service or not sync_service.keycloak_admin:
                    logger.error("Sync service not available for scheduled sync")
                    return
                
                # Run full sync
                results = sync_service.sync_all(dry_run=False)
                
                # Store results
                self.last_sync_results = {
                    'timestamp': datetime.utcnow(),
                    'results': results,
                    'scheduled': True
                }
                
                # Add to history (keep last 10)
                self.sync_history.append(self.last_sync_results)
                if len(self.sync_history) > 10:
                    self.sync_history.pop(0)
                
                # Log results
                if results.get('success', False):
                    summary = results.get('summary', {})
                    logger.info(f"Scheduled sync completed successfully: "
                              f"created_in_keycloak={summary.get('personas_created_in_keycloak', 0)}, "
                              f"created_locally={summary.get('personas_created_locally', 0)}, "
                              f"synchronized={summary.get('records_synchronized', 0)}, "
                              f"errors={summary.get('total_errors', 0)}")
                else:
                    errors = results.get('errors', ['Unknown error'])
                    logger.error(f"Scheduled sync failed: {', '.join(errors)}")
                
            except Exception as e:
                logger.error(f"Error in scheduled sync: {e}")
                self.last_sync_results = {
                    'timestamp': datetime.utcnow(),
                    'results': {'success': False, 'error': str(e)},
                    'scheduled': True
                }
    
    def start(self):
        """Start the scheduler in a background thread."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("Sync scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        schedule.clear()
        logger.info("Sync scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def get_next_sync_time(self) -> Optional[datetime]:
        """Get the next scheduled sync time."""
        try:
            jobs = schedule.get_jobs()
            if not jobs:
                return None
            
            next_run = min(job.next_run for job in jobs)
            return next_run
        except Exception as e:
            logger.error(f"Error getting next sync time: {e}")
            return None
    
    def get_last_sync_results(self) -> Dict[str, Any]:
        """Get results from the last synchronization."""
        return self.last_sync_results
    
    def get_sync_history(self) -> list:
        """Get synchronization history."""
        return self.sync_history.copy()
    
    def is_scheduler_running(self) -> bool:
        """Check if scheduler is running."""
        return self.is_running and self.scheduler_thread and self.scheduler_thread.is_alive()
    
    def run_manual_sync(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run manual synchronization (not scheduled)."""
        if not self.app:
            return {'success': False, 'error': 'Flask app not initialized'}
        
        with self.app.app_context():
            try:
                sync_service = get_sync_service()
                if not sync_service or not sync_service.keycloak_admin:
                    return {'success': False, 'error': 'Sync service not available'}
                
                results = sync_service.sync_all(dry_run=dry_run)
                
                # Store results if not dry run
                if not dry_run:
                    self.last_sync_results = {
                        'timestamp': datetime.utcnow(),
                        'results': results,
                        'scheduled': False
                    }
                    
                    self.sync_history.append(self.last_sync_results)
                    if len(self.sync_history) > 10:
                        self.sync_history.pop(0)
                
                return results
                
            except Exception as e:
                logger.error(f"Error in manual sync: {e}")
                return {'success': False, 'error': str(e)}


# Global scheduler instance
_scheduler = None

def get_scheduler() -> SyncScheduler:
    """Get global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SyncScheduler()
    return _scheduler

def init_scheduler(app: Flask):
    """Initialize scheduler with Flask app."""
    scheduler = get_scheduler()
    scheduler.init_app(app)
    
    # Start scheduler if configured
    if app.config.get('KEYCLOAK_SYNC_ENABLE_SCHEDULER', False):
        scheduler.start()
    
    return scheduler
