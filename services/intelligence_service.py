from utils.pg_wrapper import qry, qone
from datetime import datetime, timedelta

class IntelligenceService:
    @staticmethod
    def get_attendance_insights(dept=None, year=None, division=None):
        """
        Calculates high-level intelligence insights for attendance data.
        """
        insights = {
            "risk_profiles": [],
            "top_performers": [],
            "attendance_trend": [],
            "subject_anomalies": [],
            "predictions": []
        }

        # 1. Identity Critical Defaulters (Risk Profiles)
        risk_sql = """
            SELECT s.id, s.name, s.roll, s.department, s.division,
                   COUNT(a.id) as total_sessions,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present,
                   ROUND(SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(a.id),0), 1) as percentage
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id
            WHERE 1=1
        """
        params = []
        if dept: risk_sql += " AND s.department=%s"; params.append(dept)
        if year: risk_sql += " AND s.year=%s"; params.append(year)
        if division: risk_sql += " AND s.division=%s"; params.append(division)
        
        risk_sql += " GROUP BY s.id ORDER BY (SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(a.id),0)) ASC LIMIT 10"
        insights["risk_profiles"] = qry(risk_sql, params)

        # 2. Attendance Trend (Last 8 Weeks)
        trend_sql = """
            SELECT TO_CHAR(date_trunc('week', date), 'YYYY-WW') as week,
                   AVG(CASE WHEN status='Present' THEN 100 ELSE 0 END) as avg_pct
            FROM attendance
            WHERE date > CURRENT_DATE - INTERVAL '8 weeks'
            GROUP BY 1 ORDER BY 1
        """
        insights["attendance_trend"] = qry(trend_sql)

        # 3. Subject-wise Participation Anomaly
        # Detect subjects with significantly lower attendance than others
        anomaly_sql = """
            SELECT subject, 
                   COUNT(*) as total,
                   AVG(CASE WHEN status='Present' THEN 100 ELSE 0 END) as avg_pct
            FROM attendance
            GROUP BY subject
            HAVING AVG(CASE WHEN status='Present' THEN 100 ELSE 0 END) < (SELECT AVG(CASE WHEN status='Present' THEN 100 ELSE 0 END) FROM attendance) - 10
            ORDER BY avg_pct ASC
        """
        insights["subject_anomalies"] = qry(anomaly_sql)

        return insights

    @staticmethod
    def predict_defaulters(student_id):
        """
        Predicts if a student will become a defaulter based on recent 5 sessions.
        """
        recent = qry("""
            SELECT status FROM attendance 
            WHERE student_id = %s 
            ORDER BY date DESC LIMIT 5
        """, (student_id,))
        
        if not recent: return {"status": "stable", "risk": "low"}
        
        present = sum(1 for r in recent if r['status'] == 'Present')
        if present <= 2: return {"status": "declining", "risk": "high"}
        if present <= 3: return {"status": "unstable", "risk": "medium"}
        return {"status": "steady", "risk": "low"}
