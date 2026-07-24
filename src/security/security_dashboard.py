from src.database.db_manager import get_db_connection


def get_overview():
    """KPIs + évolution quotidienne (14 jours) pour le dashboard cybersécurité admin."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM security_events WHERE created_at >= NOW() - INTERVAL '24 hours';"
        )
        events_24h = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM security_events "
            "WHERE action = 'login' AND status = 'FAILED' AND created_at >= NOW() - INTERVAL '24 hours';"
        )
        failed_logins_24h = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM security_events "
            "WHERE status IN ('BLOCKED', 'CRITICAL') AND created_at >= NOW() - INTERVAL '24 hours';"
        )
        attacks_24h = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(DISTINCT username) FROM security_events WHERE action = 'user_session_ban';"
        )
        total_bans = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT
                date_trunc('day', created_at) AS day,
                COUNT(*) FILTER (WHERE status IN ('BLOCKED', 'CRITICAL')) AS attacks,
                COUNT(*) FILTER (WHERE action = 'login' AND status = 'FAILED') AS failed_logins,
                COUNT(*) FILTER (WHERE action = 'login' AND status = 'SUCCESS') AS successful_logins
            FROM security_events
            WHERE created_at >= NOW() - INTERVAL '14 days'
            GROUP BY day
            ORDER BY day;
            """
        )
        timeseries = [
            {
                "day": day.strftime("%Y-%m-%d"),
                "attacks": attacks,
                "failed_logins": failed_logins,
                "successful_logins": successful_logins,
            }
            for day, attacks, failed_logins, successful_logins in cursor.fetchall()
        ]

        cursor.close()
    finally:
        conn.close()

    return {
        "kpis": {
            "events_24h": events_24h,
            "failed_logins_24h": failed_logins_24h,
            "attacks_24h": attacks_24h,
            "total_bans": total_bans,
        },
        "timeseries": timeseries,
    }


def get_events(limit=100, status=None, action=None):
    """Derniers événements de sécurité, du plus récent au plus ancien."""
    conditions = []
    params = []
    if status:
        conditions.append("status = ANY(%s)")
        params.append(status if isinstance(status, list) else [status])
    if action:
        conditions.append("action = ANY(%s)")
        params.append(action if isinstance(action, list) else [action])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT event_id, username, role, action, status, details, created_at
            FROM security_events
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            params,
        )
        rows = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    return [
        {
            "event_id": event_id,
            "username": username,
            "role": role,
            "action": action,
            "status": status,
            "details": details,
            "created_at": created_at.isoformat(),
        }
        for event_id, username, role, action, status, details, created_at in rows
    ]
