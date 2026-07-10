"""
Lucide icon set (https://lucide.dev) — ISC licence.

Each icon is a raw inline SVG string. `currentColor` is used for the stroke,
so the icon automatically inherits the colour of its parent container.
"""


def _svg(paths: str, size: int = 22) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    )


# --- KPI icons -------------------------------------------------------------

# dollar-sign
ICON_SALES = _svg(
    '<line x1="12" x2="12" y1="2" y2="22"/>'
    '<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'
)

# trending-up
ICON_PROFIT = _svg(
    '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
    '<polyline points="16 7 22 7 22 13"/>'
)

# triangle-alert
ICON_ANOMALY = _svg(
    '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
    '<path d="M12 9v4"/><path d="M12 17h.01"/>'
)

# percent
ICON_MARGIN = _svg(
    '<line x1="19" x2="5" y1="5" y2="19"/>'
    '<circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>'
)

# truck
ICON_SHIPPING = _svg(
    '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/>'
    '<path d="M15 18H9"/>'
    '<path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/>'
    '<circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>'
)

# tag
ICON_DISCOUNT = _svg(
    '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 '
    '2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/>'
    '<circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>'
)


# --- Sidebar / status icons -----------------------------------------------

# user
ICON_USER = _svg('<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>', size=18)

# database
ICON_DATABASE = _svg(
    '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
    '<path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>', size=16
)

# bar-chart-3
ICON_CHART = _svg('<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>', size=16)

# lock
ICON_LOCK = _svg('<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>', size=16)

# log-out
ICON_LOGOUT = _svg(
    '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
    '<polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>', size=16
)

# search-code (SQL detail)
ICON_SQL = _svg(
    '<path d="m9 9-2 2 2 2"/><path d="m13 13 2-2-2-2"/>'
    '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>', size=16
)

# bot
ICON_BOT = _svg(
    '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/>'
    '<path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>', size=18
)