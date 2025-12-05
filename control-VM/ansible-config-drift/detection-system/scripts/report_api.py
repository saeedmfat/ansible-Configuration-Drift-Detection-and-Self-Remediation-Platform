#!/usr/bin/env python3
"""
Flask API server for serving drift detection reports.
"""

from flask import Flask, jsonify, render_template_string, send_file, abort
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
REPORTS_BASE_DIR = "reports"
API_VERSION = "1.0"

# HTML template for web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drift Detection Reports API</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
        h1 { margin: 0; }
        .api-info { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .endpoint { background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 10px 0; }
        .endpoint h3 { margin: 0 0 10px 0; }
        .method { display: inline-block; padding: 3px 8px; background: #3498db; color: white; border-radius: 3px; font-size: 0.9em; margin-right: 10px; }
        .reports-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 30px; }
        .report-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .report-card h3 { margin: 0 0 10px 0; color: #2c3e50; }
        .severity { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; margin-right: 5px; }
        .severity-critical { background: #dc3545; color: white; }
        .severity-high { background: #fd7e14; color: white; }
        .severity-medium { background: #ffc107; color: white; }
        .severity-low { background: #28a745; color: white; }
        .timestamp { color: #6c757d; font-size: 0.9em; }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Drift Detection Reports API</h1>
            <p>Version {{ api_version }} • {{ total_reports }} reports available</p>
        </header>
        
        <div class="api-info">
            <h2>📚 API Endpoints</h2>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/v1/reports</h3>
                <p>Get list of all available reports.</p>
                <code><a href="/api/v1/reports">/api/v1/reports</a></code>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/v1/reports/latest</h3>
                <p>Get the latest drift detection report.</p>
                <code><a href="/api/v1/reports/latest">/api/v1/reports/latest</a></code>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/v1/reports/date/YYYY/MM/DD</h3>
                <p>Get reports for a specific date.</p>
                <code><a href="/api/v1/reports/date/{{ today.strftime('%Y/%m/%d') }}">/api/v1/reports/date/{{ today.strftime('%Y/%m/%d') }}</a></code>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/v1/reports/id/&lt;report_id&gt;</h3>
                <p>Get a specific report by ID.</p>
                <code>/api/v1/reports/id/&lt;report_id&gt;</code>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/v1/summary</h3>
                <p>Get summary statistics.</p>
                <code><a href="/api/v1/summary">/api/v1/summary</a></code>
            </div>
        </div>
        
        {% if recent_reports %}
        <div class="api-info">
            <h2>📋 Recent Reports</h2>
            <div class="reports-grid">
                {% for report in recent_reports %}
                <div class="report-card">
                    <h3>
                        <a href="/api/v1/reports/id/{{ report.id }}">
                            {{ report.id }}
                        </a>
                    </h3>
                    <p class="timestamp">{{ report.timestamp }}</p>
                    <p><strong>Detections:</strong> {{ report.detections }}</p>
                    <div>
                        {% for severity, count in report.severities.items() %}
                        <span class="severity severity-{{ severity }}">{{ severity.upper() }}: {{ count }}</span>
                        {% endfor %}
                    </div>
                    <p style="margin-top: 10px;">
                        <a href="/api/v1/reports/id/{{ report.id }}/json">JSON</a> • 
                        <a href="/api/v1/reports/id/{{ report.id }}/html">HTML</a> • 
                        <a href="/api/v1/reports/id/{{ report.id }}/markdown">Markdown</a>
                    </p>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <footer style="text-align: center; margin-top: 40px; color: #6c757d;">
            <p>Drift Detection Platform • Generated on {{ generated_time }}</p>
        </footer>
    </div>
</body>
</html>
"""

def find_reports():
    """Find all report files."""
    reports = []
    
    for json_file in Path(REPORTS_BASE_DIR).rglob("*.json"):
        try:
            with open(json_file, 'r') as f:
                report_data = json.load(f)
            
            # Extract report ID from filename
            report_id = json_file.stem.replace('detection_', '').replace('report_', '')
            
            reports.append({
                "id": report_id,
                "path": str(json_file),
                "timestamp": report_data.get('metadata', {}).get('timestamp', ''),
                "detections": report_data.get('summary', {}).get('total_detections', 0),
                "severities": report_data.get('summary', {}).get('by_severity', {}),
                "data": report_data
            })
        except Exception as e:
            logger.warning(f"Error reading report {json_file}: {str(e)}")
    
    # Sort by timestamp (newest first)
    reports.sort(key=lambda x: x['timestamp'], reverse=True)
    return reports

@app.route('/')
def index():
    """Home page with API documentation."""
    reports = find_reports()
    
    # Get recent reports (last 5)
    recent_reports = reports[:5]
    
    return render_template_string(HTML_TEMPLATE, 
        api_version=API_VERSION,
        total_reports=len(reports),
        recent_reports=recent_reports,
        today=datetime.now(),
        generated_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

@app.route('/api/v1/reports', methods=['GET'])
def get_all_reports():
    """Get list of all available reports."""
    reports = find_reports()
    
    # Return minimal info for listing
    report_list = []
    for report in reports:
        report_list.append({
            "id": report['id'],
            "timestamp": report['timestamp'],
            "detections": report['detections'],
            "severities": report['severities'],
            "path": report['path']
        })
    
    return jsonify({
        "api_version": API_VERSION,
        "total_reports": len(reports),
        "reports": report_list
    })

@app.route('/api/v1/reports/latest', methods=['GET'])
def get_latest_report():
    """Get the latest report."""
    reports = find_reports()
    
    if not reports:
        return jsonify({"error": "No reports found"}), 404
    
    return jsonify(reports[0]['data'])

@app.route('/api/v1/reports/date/<year>/<month>/<day>', methods=['GET'])
def get_reports_by_date(year, month, day):
    """Get reports for a specific date."""
    date_str = f"{year}/{month}/{day}"
    reports_dir = Path(REPORTS_BASE_DIR) / "daily" / year / month / day
    
    if not reports_dir.exists():
        return jsonify({"error": "No reports for this date"}), 404
    
    reports = []
    for json_file in reports_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                report_data = json.load(f)
            
            report_id = json_file.stem.replace('detection_', '').replace('report_', '')
            
            reports.append({
                "id": report_id,
                "timestamp": report_data.get('metadata', {}).get('timestamp', ''),
                "detections": report_data.get('summary', {}).get('total_detections', 0),
                "data": report_data
            })
        except Exception as e:
            logger.warning(f"Error reading report {json_file}: {str(e)}")
    
    return jsonify({
        "date": date_str,
        "total_reports": len(reports),
        "reports": reports
    })

@app.route('/api/v1/reports/id/<report_id>', methods=['GET'])
def get_report_by_id(report_id):
    """Get a specific report by ID."""
    # Search for report file
    for json_file in Path(REPORTS_BASE_DIR).rglob(f"*{report_id}*.json"):
        try:
            with open(json_file, 'r') as f:
                report_data = json.load(f)
            
            return jsonify(report_data)
        except Exception as e:
            logger.warning(f"Error reading report {json_file}: {str(e)}")
    
    return jsonify({"error": "Report not found"}), 404

@app.route('/api/v1/reports/id/<report_id>/<format>', methods=['GET'])
def get_report_format(report_id, format):
    """Get report in specific format."""
    # Search for report file
    for json_file in Path(REPORTS_BASE_DIR).rglob(f"*{report_id}*.json"):
        try:
            report_path = Path(json_file)
            
            if format == "json":
                return send_file(str(report_path), mimetype='application/json')
            
            elif format == "html":
                html_file = report_path.with_suffix('.html')
                if html_file.exists():
                    return send_file(str(html_file), mimetype='text/html')
                else:
                    return jsonify({"error": "HTML version not available"}), 404
            
            elif format == "markdown":
                md_file = report_path.with_suffix('.md')
                if md_file.exists():
                    return send_file(str(md_file), mimetype='text/markdown')
                else:
                    return jsonify({"error": "Markdown version not available"}), 404
            
        except Exception as e:
            logger.warning(f"Error reading report {json_file}: {str(e)}")
    
    return jsonify({"error": "Report not found"}), 404

@app.route('/api/v1/summary', methods=['GET'])
def get_summary():
    """Get summary statistics."""
    reports = find_reports()
    
    if not reports:
        return jsonify({"error": "No reports found"}), 404
    
    # Calculate statistics
    total_detections = sum(r['detections'] for r in reports)
    
    severity_totals = {}
    for report in reports:
        for severity, count in report['severities'].items():
            severity_totals[severity] = severity_totals.get(severity, 0) + count
    
    # Group by date
    from collections import defaultdict
    reports_by_date = defaultdict(list)
    for report in reports:
        if report['timestamp']:
            date = report['timestamp'][:10]  # YYYY-MM-DD
            reports_by_date[date].append(report)
    
    return jsonify({
        "api_version": API_VERSION,
        "statistics": {
            "total_reports": len(reports),
            "total_detections": total_detections,
            "average_detections_per_report": total_detections / len(reports) if reports else 0,
            "severity_distribution": severity_totals,
            "reports_by_date": {k: len(v) for k, v in reports_by_date.items()}
        },
        "time_range": {
            "first_report": reports[-1]['timestamp'] if reports else None,
            "last_report": reports[0]['timestamp'] if reports else None
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "reports_count": len(find_reports())
    })

if __name__ == '__main__':
    # Ensure reports directory exists
    os.makedirs(REPORTS_BASE_DIR, exist_ok=True)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=8080, debug=True)
