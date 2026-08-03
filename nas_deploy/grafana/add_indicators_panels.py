#!/usr/bin/env python3
"""Add technical indicator panels to the BRVM Grafana dashboard."""

import json
import urllib.request
import base64

GRAFANA_URL = "http://brvm-grafana:3000"
DASHBOARD_UID = "brvm-main-dashboard"
AUTH = base64.b64encode(b"admin:admin123").decode()

def api(method, path, data=None):
    url = f"{GRAFANA_URL}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Basic {AUTH}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get_dashboard():
    return api("GET", f"/api/dashboards/uid/{DASHBOARD_UID}")

def save_dashboard(dashboard_json):
    return api("POST", "/api/dashboards/db", {"dashboard": dashboard_json, "overwrite": True})

DS = {"type": "postgres", "uid": "bfu05lo1ogsg0c"}
TICKER_VAR = "$ticker"
BASE_W = 24

def make_rsi_panel(x, y, w, h, panel_id):
    return {
        "datasource": DS, "id": panel_id,
        "title": "RSI (14)",
        "type": "timeseries",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"drawStyle": "line", "fillOpacity": 10, "lineWidth": 2, "pointSize": 4, "showPoints": "never"},
                "min": 0, "max": 100, "unit": "short",
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "#73BF69", "value": None},
                        {"color": "transparent", "value": 30},
                        {"color": "#F2495C", "value": 70},
                        {"color": "transparent", "value": 100},
                    ]
                }
            }, "overrides": []
        },
        "options": {
            "legend": {"calcs": ["lastNotNull"], "displayMode": "table", "placement": "bottom"},
            "tooltip": {"mode": "single"}
        },
        "targets": [{
            "datasource": DS, "format": "time_series", "refId": "A",
            "rawSql": f"""SELECT date as "time", rsi_14 as "RSI 14"
                FROM indicators
                WHERE ticker = '{TICKER_VAR}' AND rsi_14 IS NOT NULL
                  AND date >= (SELECT MAX(date) - INTERVAL '90 days' FROM indicators WHERE ticker = '{TICKER_VAR}')
                ORDER BY date;"""
        }]
    }

def make_macd_panel(x, y, w, h, panel_id):
    return {
        "datasource": DS, "id": panel_id,
        "title": "MACD (12, 26, 9)",
        "type": "timeseries",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"drawStyle": "line", "fillOpacity": 15, "lineWidth": 2, "pointSize": 0, "showPoints": "never"},
                "unit": "short"
            }, "overrides": [
                {"matcher": {"id": "byName", "options": "Histogram"}, "properties": [
                    {"id": "custom.drawStyle", "value": "bars"},
                    {"id": "custom.fillOpacity", "value": 60},
                    {"id": "custom.thresholdsStyle", "value": {"mode": "line"}},
                ]}
            ]
        },
        "options": {
            "legend": {"calcs": ["lastNotNull"], "displayMode": "table", "placement": "bottom"},
            "tooltip": {"mode": "multi", "sort": "desc"}
        },
        "targets": [{
            "datasource": DS, "format": "time_series", "refId": "A",
            "rawSql": f"""SELECT date as "time",
                    macd_line as "MACD",
                    macd_signal as "Signal",
                    macd_histogram as "Histogram"
                FROM indicators
                WHERE ticker = '{TICKER_VAR}' AND macd_line IS NOT NULL
                  AND date >= (SELECT MAX(date) - INTERVAL '90 days' FROM indicators WHERE ticker = '{TICKER_VAR}')
                ORDER BY date;"""
        }]
    }

def make_bb_panel(x, y, w, h, panel_id):
    return {
        "datasource": DS, "id": panel_id,
        "title": "Bollinger Bands (20, 2)",
        "type": "timeseries",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"drawStyle": "line", "fillOpacity": 10, "lineWidth": 2, "pointSize": 3, "showPoints": "never"},
                "unit": "currency"
            }, "overrides": [
                {"matcher": {"id": "byName", "options": "Bande Sup."}, "properties": [
                    {"id": "custom.fillOpacity", "value": 0},
                    {"id": "custom.lineStyle", "value": {"dash": [8, 4], "fill": "dash"}},
                    {"id": "color", "value": {"fixedColor": "#F2495C", "mode": "fixed"}},
                ]},
                {"matcher": {"id": "byName", "options": "Bande Inf."}, "properties": [
                    {"id": "custom.fillOpacity", "value": 0},
                    {"id": "custom.lineStyle", "value": {"dash": [8, 4], "fill": "dash"}},
                    {"id": "color", "value": {"fixedColor": "#73BF69", "mode": "fixed"}},
                ]},
                {"matcher": {"id": "byName", "options": "Moyenne"}, "properties": [
                    {"id": "color", "value": {"fixedColor": "#FADE2A", "mode": "fixed"}},
                ]},
            ]
        },
        "options": {
            "legend": {"calcs": ["lastNotNull"], "displayMode": "table", "placement": "bottom"},
            "tooltip": {"mode": "multi", "sort": "desc"}
        },
        "targets": [{
            "datasource": DS, "format": "time_series", "refId": "A",
            "rawSql": f"""SELECT date as "time",
                    close as "Prix",
                    bb_upper as "Bande Sup.",
                    bb_middle as "Moyenne",
                    bb_lower as "Bande Inf."
                FROM indicators
                WHERE ticker = '{TICKER_VAR}' AND bb_upper IS NOT NULL
                  AND date >= (SELECT MAX(date) - INTERVAL '90 days' FROM indicators WHERE ticker = '{TICKER_VAR}')
                ORDER BY date;"""
        }]
    }

def make_stoch_panel(x, y, w, h, panel_id):
    return {
        "datasource": DS, "id": panel_id,
        "title": "Stochastique (14)",
        "type": "timeseries",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"drawStyle": "line", "fillOpacity": 10, "lineWidth": 2, "pointSize": 0, "showPoints": "never"},
                "min": 0, "max": 100, "unit": "short",
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "#73BF69", "value": None},
                        {"color": "transparent", "value": 20},
                        {"color": "#F2495C", "value": 80},
                        {"color": "transparent", "value": 100},
                    ]
                }
            }, "overrides": [
                {"matcher": {"id": "byName", "options": "%D"}, "properties": [
                    {"id": "custom.lineStyle", "value": {"dash": [6, 3], "fill": "dash"}},
                ]}
            ]
        },
        "options": {
            "legend": {"calcs": ["lastNotNull"], "displayMode": "table", "placement": "bottom"},
            "tooltip": {"mode": "multi", "sort": "desc"}
        },
        "targets": [{
            "datasource": DS, "format": "time_series", "refId": "A",
            "rawSql": f"""SELECT date as "time", stoch_k as "%K", stoch_d as "%D"
                FROM indicators
                WHERE ticker = '{TICKER_VAR}' AND stoch_k IS NOT NULL
                  AND date >= (SELECT MAX(date) - INTERVAL '90 days' FROM indicators WHERE ticker = '{TICKER_VAR}')
                ORDER BY date;"""
        }]
    }

def make_signals_table(x, y, w, h, panel_id):
    return {
        "datasource": DS, "id": panel_id,
        "title": "Signaux Recents",
        "type": "table",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "fieldConfig": {
            "defaults": {"custom": {"align": "auto", "cellOptions": {"type": "auto"}}},
            "overrides": [
                {"matcher": {"id": "byName", "options": "Signal"}, "properties": [
                    {"id": "custom.cellOptions", "value": {
                        "mode": "basic",
                        "type": "color-background"
                    }},
                    {"id": "thresholds", "value": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "#73BF69", "value": None},
                            {"color": "transparent", "value": 1},
                            {"color": "#F2495C", "value": 2},
                        ]
                    }},
                    {"id": "mappings", "value": [
                        {"options": {"BUY": {"text": "ACHETER", "index": 0}, "SELL": {"text": "VENDRE", "index": 1}, "HOLD": {"text": "GARDER", "index": 2}}, "type": "value"}
                    ]}
                ]},
                {"matcher": {"id": "byName", "options": "Confiance"}, "properties": [
                    {"id": "unit", "value": "percent"},
                    {"id": "custom.cellOptions", "value": {"mode": "gradient", "type": "gauge"}},
                    {"id": "thresholds", "value": {"mode": "absolute", "steps": [
                        {"color": "#F2495C", "value": None},
                        {"color": "#FF9830", "value": 50},
                        {"color": "#73BF69", "value": 75},
                    ]}}
                ]}
            ]
        },
        "options": {"cellHeight": "sm", "showHeader": True},
        "targets": [{
            "datasource": DS, "format": "table", "refId": "A",
            "rawSql": f"""SELECT date as "Date", signal_type as "Signal",
                    ROUND(confidence * 100, 1) as "Confiance",
                    indicator as "Indicateur", reason as "Raison",
                    price_at_signal as "Prix"
                FROM signals
                WHERE ticker = '{TICKER_VAR}'
                ORDER BY date DESC LIMIT 20;"""
        }]
    }

def make_sma_panel(x, y, w, h, panel_id):
    return {
        "datasource": DS, "id": panel_id,
        "title": "Moyennes Mobiles (SMA 20/50/200)",
        "type": "timeseries",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"drawStyle": "line", "fillOpacity": 5, "lineWidth": 2, "pointSize": 0, "showPoints": "never"},
                "unit": "currency"
            }, "overrides": [
                {"matcher": {"id": "byName", "options": "SMA 20"}, "properties": [
                    {"id": "color", "value": {"fixedColor": "#FADE2A", "mode": "fixed"}},
                ]},
                {"matcher": {"id": "byName", "options": "SMA 50"}, "properties": [
                    {"id": "color", "value": {"fixedColor": "#FF9830", "mode": "fixed"}},
                ]},
                {"matcher": {"id": "byName", "options": "SMA 200"}, "properties": [
                    {"id": "color", "value": {"fixedColor": "#F2495C", "mode": "fixed"}},
                    {"id": "custom.lineStyle", "value": {"dash": [10, 5], "fill": "dash"}},
                ]},
                {"matcher": {"id": "byName", "options": "Prix"}, "properties": [
                    {"id": "color", "value": {"fixedColor": "#8AB8FF", "mode": "fixed"}},
                    {"id": "custom.lineWidth", "value": 3},
                ]},
            ]
        },
        "options": {
            "legend": {"calcs": ["lastNotNull"], "displayMode": "table", "placement": "bottom"},
            "tooltip": {"mode": "multi", "sort": "desc"}
        },
        "targets": [{
            "datasource": DS, "format": "time_series", "refId": "A",
            "rawSql": f"""SELECT date as "time",
                    close as "Prix",
                    sma_20 as "SMA 20",
                    sma_50 as "SMA 50",
                    sma_200 as "SMA 200"
                FROM indicators
                WHERE ticker = '{TICKER_VAR}' AND sma_20 IS NOT NULL
                  AND date >= (SELECT MAX(date) - INTERVAL '180 days' FROM indicators WHERE ticker = '{TICKER_VAR}')
                ORDER BY date;"""
        }]
    }

def main():
    print("Fetching dashboard...")
    resp = get_dashboard()
    dash = resp["dashboard"]

    existing_ids = set()
    for p in dash["panels"]:
        existing_ids.add(p["id"])
        if "panels" in p:
            for sub in p["panels"]:
                existing_ids.add(sub["id"])

    max_id = max(existing_ids) if existing_ids else 100
    base_y = 81

    new_panels = [
        {"type": "row", "id": max_id + 1, "title": "Indicateurs Techniques", "gridPos": {"h": 1, "w": 24, "x": 0, "y": base_y}, "collapsed": False},
        make_rsi_panel(0, base_y + 1, 12, 8, max_id + 2),
        make_stoch_panel(12, base_y + 1, 12, 8, max_id + 3),
        make_macd_panel(0, base_y + 9, 12, 8, max_id + 4),
        make_bb_panel(12, base_y + 9, 12, 8, max_id + 5),
        make_sma_panel(0, base_y + 17, 16, 8, max_id + 6),
        make_signals_table(16, base_y + 17, 8, 8, max_id + 7),
    ]

    dash["panels"].extend(new_panels)

    print("Saving dashboard...")
    result = save_dashboard(dash)
    print(f"Done! Dashboard URL: {result.get('url', 'N/A')}")
    print(f"Added {len(new_panels)} new panels (ids {max_id+1}-{max_id+len(new_panels)})")

if __name__ == "__main__":
    main()
