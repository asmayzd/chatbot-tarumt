import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


class Forecaster:
    """Monthly time-series forecasting on top of KPIAnalyzer.monthly_trends().

    Holt-Winters exponential smoothing: additive trend, plus an additive yearly
    seasonal component once there is enough history to fit one reliably.
    """

    METRICS = ("sales", "profit", "order_count")
    NON_NEGATIVE_METRICS = ("sales", "order_count")  # profit alone can legitimately go negative
    MIN_POINTS = 4          # below this, a fitted trend is not meaningful
    SEASONAL_MIN_POINTS = 24  # need >= 2 full yearly cycles to fit seasonality

    def __init__(self, kpi_analyzer):
        self.kpi = kpi_analyzer

    def forecast(self, metric: str, periods: int = 3) -> dict | None:
        """Returns None when there isn't enough monthly history to forecast from."""
        if metric not in self.METRICS:
            raise ValueError(f"Unknown metric: {metric}")

        trends = self.kpi.monthly_trends()
        if trends is None or len(trends) < self.MIN_POINTS:
            return None

        trends = trends.sort_values("period")
        series = pd.Series(
            trends[metric].astype(float).values,
            index=pd.PeriodIndex(trends["period"], freq="M"),
        )
        # Fill any missing month with 0 (no orders that month) so Holt-Winters sees a
        # continuous, evenly-spaced series. Series.asfreq() does NOT do this for a
        # PeriodIndex already tagged "M" — it's a no-op — so reindex explicitly.
        full_range = pd.period_range(series.index.min(), series.index.max(), freq="M")
        series = series.reindex(full_range, fill_value=0.0)

        has_seasonality = len(series) >= self.SEASONAL_MIN_POINTS
        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal="add" if has_seasonality else None,
            seasonal_periods=12 if has_seasonality else None,
            initialization_method="estimated",
        )
        fit = model.fit(optimized=True)
        forecast_values = fit.forecast(periods)
        if metric in self.NON_NEGATIVE_METRICS:
            forecast_values = forecast_values.clip(lower=0)
        future_index = pd.period_range(series.index[-1] + 1, periods=periods, freq="M")

        return {
            "metric": metric,
            "historical_labels": [str(p) for p in series.index],
            "historical_values": [round(float(v), 2) for v in series.values],
            "forecast_labels": [str(p) for p in future_index],
            "forecast_values": [round(float(v), 2) for v in forecast_values],
        }
