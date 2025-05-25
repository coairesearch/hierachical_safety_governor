"""Synchronous pub/sub event bus used by referees & governor."""
import logging
from typing import Callable, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Global subscribers dictionary
_subs: Dict[str, List[Callable[[str, Any], None]]] = {}

# Configuration for error handling
_config = {
    'fail_on_handler_error': False,  # If True, stops processing on first error
    'log_errors': True,              # If True, logs handler errors
    'max_retries': 0                 # Number of retries for failed handlers
}

def subscribe(event_type: str, handler: Callable[[str, Any], None]) -> None:
    """Subscribe a handler to an event type.
    
    Args:
        event_type: The type of event to subscribe to
        handler: Callable that takes (event_type, payload) as arguments
    """
    if not event_type:
        raise ValueError("Event type cannot be empty")
    if not callable(handler):
        raise TypeError(f"Handler must be callable, got {type(handler)}")
        
    _subs.setdefault(event_type, []).append(handler)
    logger.debug(f"Handler {handler.__name__} subscribed to '{event_type}'")

def publish(event_type: str, payload: Any) -> None:
    """Publish an event to all subscribers.
    
    Args:
        event_type: The type of event to publish
        payload: The event data to send to handlers
    """
    if not event_type:
        raise ValueError("Event type cannot be empty")
        
    handlers = _subs.get(event_type, [])
    if not handlers:
        logger.debug(f"No handlers registered for event type '{event_type}'")
        return
        
    logger.debug(f"Publishing event '{event_type}' to {len(handlers)} handlers")
    
    failed_handlers = []
    for handler in handlers:
        retries = 0
        while retries <= _config['max_retries']:
            try:
                handler(event_type, payload)
                break  # Success, exit retry loop
            except Exception as e:
                retries += 1
                handler_name = getattr(handler, '__name__', str(handler))
                
                if retries > _config['max_retries']:
                    # Final failure
                    error_msg = f"Handler {handler_name} failed for event '{event_type}': {e}"
                    if _config['log_errors']:
                        logger.error(error_msg, exc_info=True)
                    failed_handlers.append((handler, e))
                    
                    if _config['fail_on_handler_error']:
                        raise RuntimeError(error_msg) from e
                else:
                    # Retry
                    logger.warning(f"Handler {handler_name} failed, retrying ({retries}/{_config['max_retries']})")
    
    if failed_handlers and _config['log_errors']:
        logger.warning(f"{len(failed_handlers)} handlers failed for event '{event_type}'")

def unsubscribe(event_type: str, handler: Callable[[str, Any], None]) -> bool:
    """Unsubscribe a handler from an event type.
    
    Args:
        event_type: The type of event to unsubscribe from
        handler: The handler to remove
        
    Returns:
        True if handler was removed, False if not found
    """
    if event_type in _subs and handler in _subs[event_type]:
        _subs[event_type].remove(handler)
        logger.debug(f"Handler {handler.__name__} unsubscribed from '{event_type}'")
        
        # Clean up empty lists
        if not _subs[event_type]:
            del _subs[event_type]
            
        return True
    return False

def clear_all() -> None:
    """Remove all event subscriptions. Useful for testing."""
    _subs.clear()
    logger.debug("All event subscriptions cleared")

def get_subscribers(event_type: Optional[str] = None) -> Dict[str, List[Callable]]:
    """Get current subscribers, optionally filtered by event type.
    
    Args:
        event_type: If provided, only return subscribers for this event type
        
    Returns:
        Dictionary of event types to handler lists
    """
    if event_type:
        return {event_type: _subs.get(event_type, [])}
    return _subs.copy()

def configure(fail_on_handler_error: Optional[bool] = None,
              log_errors: Optional[bool] = None,
              max_retries: Optional[int] = None) -> None:
    """Configure event bus behavior.
    
    Args:
        fail_on_handler_error: If True, stop processing on first handler error
        log_errors: If True, log handler errors
        max_retries: Number of times to retry failed handlers
    """
    if fail_on_handler_error is not None:
        _config['fail_on_handler_error'] = fail_on_handler_error
    if log_errors is not None:
        _config['log_errors'] = log_errors
    if max_retries is not None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        _config['max_retries'] = max_retries
        
    logger.debug(f"Event bus configured: {_config}")