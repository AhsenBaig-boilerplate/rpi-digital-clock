"""
Health Service - UI heartbeat monitoring
Detects if UI is frozen or unresponsive
"""
import time
from typing import Optional, Callable
from threading import Thread, Event


class HealthService:
    """
    Monitor UI responsiveness via heartbeat mechanism.
    """
    
    def __init__(self, heartbeat_interval: int = 5, timeout: int = 15):
        """
        Initialize health service.
        
        Args:
            heartbeat_interval: Expected heartbeat frequency (seconds)
            timeout: Time before marking UI as frozen (seconds)
        """
        self._heartbeat_interval = heartbeat_interval
        self._timeout = timeout
        
        self._last_heartbeat: float = time.time()
        self._is_healthy: bool = True
        self._monitoring: bool = False
        self._monitor_thread: Optional[Thread] = None
        self._stop_event: Event = Event()
        
        self._on_freeze: Optional[Callable] = None
        self._on_recover: Optional[Callable] = None
    
    def heartbeat(self) -> None:
        """
        Record heartbeat from UI thread.
        Call this from UI update loop to signal responsiveness.
        """
        now = time.time()
        was_frozen = not self._is_healthy
        
        self._last_heartbeat = now
        self._is_healthy = True
        
        # Trigger recovery callback if recovering from freeze
        if was_frozen and self._on_recover:
            try:
                self._on_recover()
            except Exception as e:
                print(f"Health recovery callback error: {e}")
    
    def start_monitoring(self) -> None:
        """Start background health monitoring thread"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._stop_event.clear()
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop"""
        while self._monitoring and not self._stop_event.is_set():
            self._check_health()
            self._stop_event.wait(self._heartbeat_interval)
    
    def _check_health(self) -> None:
        """Check if UI is responsive"""
        now = time.time()
        elapsed = now - self._last_heartbeat
        
        was_healthy = self._is_healthy
        self._is_healthy = elapsed < self._timeout
        
        # Trigger freeze callback if just froze
        if was_healthy and not self._is_healthy and self._on_freeze:
            try:
                self._on_freeze()
            except Exception as e:
                print(f"Health freeze callback error: {e}")
    
    def is_healthy(self) -> bool:
        """
        Check if UI is responsive.
        
        Returns:
            True if recent heartbeat received, False if frozen
        """
        now = time.time()
        elapsed = now - self._last_heartbeat
        return elapsed < self._timeout
    
    def get_status(self) -> dict:
        """
        Get detailed health status.
        
        Returns:
            Dictionary with health metrics
        """
        now = time.time()
        elapsed = now - self._last_heartbeat
        
        return {
            'healthy': self.is_healthy(),
            'last_heartbeat': self._last_heartbeat,
            'seconds_since_heartbeat': round(elapsed, 1),
            'timeout': self._timeout,
            'monitoring': self._monitoring
        }
    
    def set_freeze_callback(self, callback: Callable) -> None:
        """
        Set callback for when UI freezes.
        
        Args:
            callback: Function to call on freeze detection
        """
        self._on_freeze = callback
    
    def set_recover_callback(self, callback: Callable) -> None:
        """
        Set callback for when UI recovers from freeze.
        
        Args:
            callback: Function to call on recovery
        """
        self._on_recover = callback
    
    def reset(self) -> None:
        """Reset health state and heartbeat timer"""
        self._last_heartbeat = time.time()
        self._is_healthy = True
    
    @property
    def timeout(self) -> int:
        """Get timeout threshold"""
        return self._timeout
    
    @timeout.setter
    def timeout(self, value: int) -> None:
        """Set timeout threshold"""
        if value > 0:
            self._timeout = value
