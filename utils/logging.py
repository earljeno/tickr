import logging

from flask import has_request_context
from flask_login import current_user

from models.models import Logs, db
from utils.network import get_client_ip
from utils.timezone import get_now

logger = logging.getLogger(__name__)


def system_log_entry(
    action: str,
    details: str,
    user_id: str | None = None,
    client_ip: str | None = None,
) -> None:
    """Record an action in the system logs safely."""
    try:
        resolved_user_id = user_id
        if not resolved_user_id and has_request_context():
            resolved_user_id = getattr(current_user, "user_id", None)
        resolved_ip = client_ip or get_client_ip()

        entry = Logs(
            action=action,
            details=details,
            user_id=resolved_user_id,
            timestamp=get_now(),
            client_ip=resolved_ip,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to record system log: {e}")


# Backwards compatibility alias
systemLogEntry = system_log_entry
