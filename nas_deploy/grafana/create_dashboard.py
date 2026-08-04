import json
import urllib.request

GRAFANA = "http://192.168.1.64:3000"
USER = "admin"
PASS = "admin123"
DS_UID = "bfu05lo1ogsg0c"

def api(method, path, data=None):
    url = f"{GRAFANA}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    import base64
    cred = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
    req.add_header("Authorization", f"Basic {cred}")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def ds():
    return {"type": "postgres", "uid": DS_UID}

dashboard = {
    "uid": "brvm-main-dashboard",
    "title": "BRVM - Tableau de bord boursier",
    "tags": ["BRVM", "Bourse", "Cote d'Ivoire", "Finance"],
    "timezone": "Africa/Abidjan",
    "time": {"from": "now-30d", "to": "now"},
    "schemaVersion": 39,
    "graphTooltip": 1,
    "editable": True,
    "templating": {
        "list": [{
            "name": "ticker",
            "type": "query",
            "datasource": ds(),
            "query": "SELECT DISTINCT ticker FROM daily ORDER BY ticker",
            "refresh": 2,
            "sort": 1,
            "current": {"text": "ABJC", "value": "ABJC"}
        }]
    },
    "panels": [
        # Row 1: Vue d'ensemble
        {"collapsed": False, "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0}, "id": 100, "title": "Vue d'ensemble du marche BRVM", "type": "row"},
        {
            "datasource": ds(), "id": 1, "type": "stat", "title": "Actions",
            "gridPos": {"h": 5, "w": 4, "x": 0, "y": 1},
            "fieldConfig": {"defaults": {"unit": "short", "thresholds": {"mode": "absolute", "steps": [{"color": "#73BF69", "value": None}]}}, "overrides": []},
            "options": {"colorMode": "value", "graphMode": "area", "justifyMode": "auto", "reduceOptions": {"calcs": ["lastNotNull"]}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT COUNT(DISTINCT ticker) as value FROM daily;", "format": "table", "refId": "A"}]
        },
        {
            "datasource": ds(), "id": 2, "type": "stat", "title": "Jours de trading",
            "gridPos": {"h": 5, "w": 5, "x": 4, "y": 1},
            "fieldConfig": {"defaults": {"unit": "short", "thresholds": {"mode": "absolute", "steps": [{"color": "#73BF69", "value": None}]}}, "overrides": []},
            "options": {"colorMode": "value", "graphMode": "area", "justifyMode": "auto", "reduceOptions": {"calcs": ["lastNotNull"]}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT COUNT(DISTINCT date) as value FROM daily;", "format": "table", "refId": "A"}]
        },
        {
            "datasource": ds(), "id": 3, "type": "stat", "title": "Premiere cotation",
            "gridPos": {"h": 5, "w": 5, "x": 9, "y": 1},
            "fieldConfig": {"defaults": {"unit": "dateTimeFromNow", "thresholds": {"mode": "absolute", "steps": [{"color": "#8AB8FF", "value": None}]}}, "overrides": []},
            "options": {"colorMode": "value", "graphMode": "none", "justifyMode": "auto", "reduceOptions": {"calcs": ["lastNotNull"]}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT TO_CHAR(MIN(date), 'DD/MM/YYYY') as value FROM daily;", "format": "table", "refId": "A"}]
        },
        {
            "datasource": ds(), "id": 4, "type": "stat", "title": "Derniere cotation",
            "gridPos": {"h": 5, "w": 5, "x": 14, "y": 1},
            "fieldConfig": {"defaults": {"unit": "dateTimeFromNow", "thresholds": {"mode": "absolute", "steps": [{"color": "#73BF69", "value": None}]}}, "overrides": []},
            "options": {"colorMode": "value", "graphMode": "none", "justifyMode": "auto", "reduceOptions": {"calcs": ["lastNotNull"]}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT TO_CHAR(MAX(date), 'DD/MM/YYYY') as value FROM daily;", "format": "table", "refId": "A"}]
        },
        {
            "datasource": ds(), "id": 5, "type": "stat", "title": "Snapshots intraday",
            "gridPos": {"h": 5, "w": 5, "x": 19, "y": 1},
            "fieldConfig": {"defaults": {"unit": "short", "thresholds": {"mode": "absolute", "steps": [{"color": "#73BF69", "value": None}]}}, "overrides": []},
            "options": {"colorMode": "value", "graphMode": "area", "justifyMode": "auto", "reduceOptions": {"calcs": ["lastNotNull"]}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT COUNT(*) as value FROM market_data;", "format": "table", "refId": "A"}]
        },

        # Row 2: Gagnants & Perdants
        {"collapsed": False, "gridPos": {"h": 1, "w": 24, "x": 0, "y": 6}, "id": 101, "title": "Mouvements du jour - Gagnants & Perdants", "type": "row"},
        {
            "datasource": ds(), "id": 10, "type": "table", "title": "Top Gagnants du jour",
            "gridPos": {"h": 12, "w": 12, "x": 0, "y": 7},
            "fieldConfig": {"defaults": {"custom": {"align": "auto", "cellOptions": {"type": "auto"}}}, "overrides": [
                {"matcher": {"id": "byName", "options": "Variation %"}, "properties": [
                    {"id": "unit", "value": "percent"},
                    {"id": "custom.cellOptions", "value": {"mode": "gradient", "type": "gauge"}},
                    {"id": "thresholds", "value": {"mode": "absolute", "steps": [{"color": "#F2495C", "value": None}, {"color": "#FF9830", "value": -5}, {"color": "#73BF69", "value": 0}]}}
                ]},
                {"matcher": {"id": "byName", "options": "Volume"}, "properties": [
                    {"id": "unit", "value": "short"},
                    {"id": "custom.cellOptions", "value": {"type": "color-background"}},
                    {"id": "thresholds", "value": {"mode": "absolute", "steps": [{"color": "transparent", "value": None}, {"color": "#73BF69", "value": 5000}, {"color": "#FF9830", "value": 20000}]}}
                ]}
            ]},
            "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
            "targets": [{"datasource": ds(), "rawSql": "WITH latest AS (SELECT ticker, date, close, volume, LAG(close) OVER (PARTITION BY ticker ORDER BY date) as prev_close FROM daily WHERE date = (SELECT MAX(date) FROM daily)) SELECT ticker as \"Action\", close as \"Dernier prix\", ROUND(((close - prev_close) / NULLIF(prev_close, 0) * 100)::numeric, 2) as \"Variation %\", volume as \"Volume\" FROM latest WHERE prev_close IS NOT NULL ORDER BY \"Variation %\" DESC LIMIT 10;", "format": "table", "refId": "A"}]
        },
        {
            "datasource": ds(), "id": 11, "type": "table", "title": "Top Perdants du jour",
            "gridPos": {"h": 12, "w": 12, "x": 12, "y": 7},
            "fieldConfig": {"defaults": {"custom": {"align": "auto", "cellOptions": {"type": "auto"}}}, "overrides": [
                {"matcher": {"id": "byName", "options": "Variation %"}, "properties": [
                    {"id": "unit", "value": "percent"},
                    {"id": "custom.cellOptions", "value": {"mode": "gradient", "type": "gauge"}},
                    {"id": "thresholds", "value": {"mode": "absolute", "steps": [{"color": "#F2495C", "value": None}, {"color": "#FF9830", "value": -5}, {"color": "#73BF69", "value": 0}]}}
                ]},
                {"matcher": {"id": "byName", "options": "Volume"}, "properties": [
                    {"id": "unit", "value": "short"},
                    {"id": "custom.cellOptions", "value": {"type": "color-background"}},
                    {"id": "thresholds", "value": {"mode": "absolute", "steps": [{"color": "transparent", "value": None}, {"color": "#73BF69", "value": 5000}, {"color": "#FF9830", "value": 20000}]}}
                ]}
            ]},
            "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
            "targets": [{"datasource": ds(), "rawSql": "WITH latest AS (SELECT ticker, date, close, volume, LAG(close) OVER (PARTITION BY ticker ORDER BY date) as prev_close FROM daily WHERE date = (SELECT MAX(date) FROM daily)) SELECT ticker as \"Action\", close as \"Dernier prix\", ROUND(((close - prev_close) / NULLIF(prev_close, 0) * 100)::numeric, 2) as \"Variation %\", volume as \"Volume\" FROM latest WHERE prev_close IS NOT NULL ORDER BY \"Variation %\" ASC LIMIT 10;", "format": "table", "refId": "A"}]
        },

        # Row 3: Toutes les actions
        {"collapsed": False, "gridPos": {"h": 1, "w": 24, "x": 0, "y": 19}, "id": 102, "title": "Toutes les actions", "type": "row"},
        {
            "datasource": ds(), "id": 20, "type": "table", "title": "Toutes les actions - Derniere journee",
            "gridPos": {"h": 16, "w": 24, "x": 0, "y": 20},
            "fieldConfig": {"defaults": {"custom": {"align": "auto", "cellOptions": {"type": "auto"}}}, "overrides": [
                {"matcher": {"id": "byName", "options": "Variation %"}, "properties": [
                    {"id": "unit", "value": "percent"},
                    {"id": "custom.cellOptions", "value": {"mode": "gradient", "type": "gauge"}},
                    {"id": "thresholds", "value": {"mode": "absolute", "steps": [{"color": "#F2495C", "value": None}, {"color": "#FF9830", "value": -3}, {"color": "transparent", "value": -0.5}, {"color": "transparent", "value": 0.5}, {"color": "#FF9830", "value": 3}, {"color": "#73BF69", "value": 5}]}}
                ]},
                {"matcher": {"id": "byName", "options": "Volume"}, "properties": [
                    {"id": "unit", "value": "short"},
                    {"id": "custom.cellOptions", "value": {"type": "color-background"}},
                    {"id": "thresholds", "value": {"mode": "absolute", "steps": [{"color": "transparent", "value": None}, {"color": "#73BF69", "value": 5000}, {"color": "#FF9830", "value": 20000}]}}
                ]}
            ]},
            "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
            "targets": [{"datasource": ds(), "rawSql": "WITH latest AS (SELECT ticker, date, open, high, low, close, volume, LAG(close) OVER (PARTITION BY ticker ORDER BY date) as prev_close, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn FROM daily) SELECT ticker as \"Action\", date as \"Date\", open as \"Ouverture\", high as \"Plus haut\", low as \"Plus bas\", close as \"Dernier prix\", volume as \"Volume\", ROUND(((close - prev_close) / NULLIF(prev_close, 0) * 100)::numeric, 2) as \"Variation %\" FROM latest WHERE rn = 1 AND prev_close IS NOT NULL ORDER BY \"Variation %\" DESC;", "format": "table", "refId": "A"}]
        },

        # Row 4: Graphiques
        {"collapsed": False, "gridPos": {"h": 1, "w": 24, "x": 0, "y": 36}, "id": 103, "title": "Graphiques temporels", "type": "row"},
        {
            "datasource": ds(), "id": 30, "type": "timeseries", "title": "Evolution des prix - 30 derniers jours",
            "gridPos": {"h": 12, "w": 16, "x": 0, "y": 37},
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "custom": {"drawStyle": "line", "fillOpacity": 10, "lineWidth": 2, "pointSize": 4, "showPoints": "auto", "lineInterpolation": "smooth", "stacking": {"mode": "none"}}, "unit": "currency", "min": 0}, "overrides": []},
            "options": {"legend": {"calcs": ["lastNotNull"], "displayMode": "table", "placement": "bottom"}, "tooltip": {"mode": "multi", "sort": "desc"}},
            "targets": [{"datasource": ds(), "rawSql": "WITH ranked AS (SELECT ticker, date, close, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn FROM daily WHERE date >= (SELECT MAX(date) - INTERVAL '30 days' FROM daily)) SELECT date as \"time\", ticker as \"metric\", close as \"Prix\" FROM ranked WHERE rn <= 30 ORDER BY date;", "format": "time_series", "refId": "A"}]
        },
        {
            "datasource": ds(), "id": 31, "type": "timeseries", "title": "Volume - 30 derniers jours",
            "gridPos": {"h": 12, "w": 8, "x": 16, "y": 37},
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "custom": {"drawStyle": "bars", "fillOpacity": 80, "gradientMode": "scheme", "stacking": {"mode": "normal"}}, "unit": "short"}, "overrides": []},
            "options": {"legend": {"calcs": ["sum"], "displayMode": "table", "placement": "right"}, "tooltip": {"mode": "multi", "sort": "desc"}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT date as \"time\", ticker as \"metric\", volume as \"Volume\" FROM daily WHERE date >= (SELECT MAX(date) - INTERVAL '30 days' FROM daily) ORDER BY date;", "format": "time_series", "refId": "A"}]
        },

        # Row 5: Detail action
        {"collapsed": False, "gridPos": {"h": 1, "w": 24, "x": 0, "y": 49}, "id": 104, "title": "Detail d'une action", "type": "row"},
        {
            "datasource": ds(), "id": 41, "type": "timeseries", "title": "Cours OHLC - 60 derniers jours",
            "gridPos": {"h": 10, "w": 16, "x": 0, "y": 50},
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "custom": {"drawStyle": "line", "fillOpacity": 10, "lineWidth": 2, "pointSize": 4, "showPoints": "always", "lineInterpolation": "smooth", "stacking": {"mode": "none"}}, "unit": "currency", "min": 0}, "overrides": [
                {"matcher": {"id": "byName", "options": "Plus haut"}, "properties": [{"id": "color", "value": {"fixedColor": "#73BF69", "mode": "fixed"}}, {"id": "custom.lineStyle", "value": {"dash": [10, 10], "fill": "dash"}}]},
                {"matcher": {"id": "byName", "options": "Plus bas"}, "properties": [{"id": "color", "value": {"fixedColor": "#F2495C", "mode": "fixed"}}, {"id": "custom.lineStyle", "value": {"dash": [10, 10], "fill": "dash"}}]}
            ]},
            "options": {"legend": {"calcs": ["lastNotNull", "min", "max", "mean"], "displayMode": "table", "placement": "bottom"}, "tooltip": {"mode": "multi", "sort": "desc"}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT date as \"time\", open as \"Ouverture\", high as \"Plus haut\", low as \"Plus bas\", close as \"Cloture\" FROM daily WHERE ticker = '$ticker' AND date >= (SELECT MAX(date) - INTERVAL '60 days' FROM daily) ORDER BY date;", "format": "time_series", "refId": "A"}]
        },
        {
            "datasource": ds(), "id": 42, "type": "timeseries", "title": "Volume - 60 derniers jours",
            "gridPos": {"h": 10, "w": 8, "x": 16, "y": 50},
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "custom": {"drawStyle": "bars", "fillOpacity": 80, "gradientMode": "scheme"}, "unit": "short"}, "overrides": []},
            "options": {"legend": {"calcs": ["sum", "mean"], "displayMode": "table", "placement": "bottom"}, "tooltip": {"mode": "single"}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT date as \"time\", volume as \"Volume\" FROM daily WHERE ticker = '$ticker' AND date >= (SELECT MAX(date) - INTERVAL '60 days' FROM daily) ORDER BY date;", "format": "time_series", "refId": "A"}]
        },

        # Row 6: Intraday
        {"collapsed": False, "gridPos": {"h": 1, "w": 24, "x": 0, "y": 60}, "id": 105, "title": "Activite intraday", "type": "row"},
        {
            "datasource": ds(), "id": 50, "type": "timeseries", "title": "Prix intraday - Aujourd'hui",
            "gridPos": {"h": 10, "w": 12, "x": 0, "y": 61},
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "custom": {"drawStyle": "line", "fillOpacity": 20, "lineWidth": 2, "lineInterpolation": "smooth", "showPoints": "auto"}, "unit": "currency"}, "overrides": []},
            "options": {"legend": {"calcs": ["lastNotNull"], "displayMode": "table", "placement": "bottom"}, "tooltip": {"mode": "multi", "sort": "desc"}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT timestamp as \"time\", ticker as \"metric\", close as \"Prix\" FROM market_data WHERE date = (SELECT MAX(date) FROM market_data) ORDER BY timestamp;", "format": "time_series", "refId": "A"}]
        },
        {
            "datasource": ds(), "id": 51, "type": "timeseries", "title": "Volume cumule intraday",
            "gridPos": {"h": 10, "w": 12, "x": 12, "y": 61},
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "custom": {"drawStyle": "bars", "fillOpacity": 80, "gradientMode": "scheme", "stacking": {"mode": "normal"}}, "unit": "short"}, "overrides": []},
            "options": {"legend": {"calcs": ["sum"], "displayMode": "table", "placement": "right"}, "tooltip": {"mode": "multi", "sort": "desc"}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT timestamp as \"time\", ticker as \"metric\", volume as \"Volume\" FROM market_data WHERE date = (SELECT MAX(date) FROM market_data) ORDER BY timestamp;", "format": "time_series", "refId": "A"}]
        },

        # Row 7: Stats
        {"collapsed": False, "gridPos": {"h": 1, "w": 24, "x": 0, "y": 71}, "id": 106, "title": "Distribution & Statistiques", "type": "row"},
        {
            "datasource": ds(), "id": 60, "type": "histogram", "title": "Distribution des variations (30j)",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 72},
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "custom": {"lineWidth": 2, "fillOpacity": 30}, "unit": "percent"}, "overrides": []},
            "options": {"legend": {"displayMode": "list", "placement": "bottom"}},
            "targets": [{"datasource": ds(), "rawSql": "WITH latest AS (SELECT ticker, close, LAG(close) OVER (PARTITION BY ticker ORDER BY date) as prev_close FROM daily WHERE date >= (SELECT MAX(date) - INTERVAL '30 days' FROM daily)) SELECT ROUND(((close - prev_close) / NULLIF(prev_close, 0) * 100)::numeric, 1) as \"Variation %\" FROM latest WHERE prev_close IS NOT NULL;", "format": "table", "refId": "A"}]
        },
        {
            "datasource": ds(), "id": 61, "type": "histogram", "title": "Distribution des volumes (30j)",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 72},
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "custom": {"lineWidth": 2, "fillOpacity": 30}, "unit": "short"}, "overrides": []},
            "options": {"legend": {"displayMode": "list", "placement": "bottom"}},
            "targets": [{"datasource": ds(), "rawSql": "SELECT volume as \"Volume\" FROM daily WHERE date >= (SELECT MAX(date) - INTERVAL '30 days' FROM daily) AND volume > 0;", "format": "table", "refId": "A"}]
        },
    ]
}

payload = {"dashboard": dashboard, "overwrite": True, "message": "BRVM Dashboard v2", "folderId": 0}
result = api("POST", "/api/dashboards/db", payload)
print(json.dumps(result, indent=2))
