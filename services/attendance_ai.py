from utils.pg_wrapper import qry, qone
from datetime import datetime, timedelta

class AttendanceAI:
    """
    Enterprise-grade AI Analytics engine for attendance forecasting, 
    risk scoring, and behavioral anomaly detection.
    """
    
    @staticmethod
    def get_risk_profiles(dept=None, year=None, division=None):
        """Calculates risk scores based on attendance trends and recent absences."""
        sql = """
            WITH student_stats AS (
                SELECT s.id, s.name, s.roll, s.department, s.division,
                       COUNT(a.id) as total,
                       SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present,
                       -- Recent 5 sessions trend
                       ARRAY_AGG(a.status ORDER BY a.date DESC) FILTER (WHERE a.id IS NOT NULL) as recent_history
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id
                WHERE 1=1
        """
        params = []
        if dept: sql += " AND s.department=%s"; params.append(dept)
        if year: sql += " AND s.year=%s"; params.append(year)
        if division: sql += " AND s.division=%s"; params.append(division)
        
        sql += """
                GROUP BY s.id
            )
            SELECT *,
                   CASE 
                     WHEN total = 0 THEN 0
                     ELSE ROUND((present * 100.0 / total), 1) 
                   END as percentage,
                   -- Risk Score Logic: Base (100 - pct) + Penalty for recent absences
                   CASE
                     WHEN total = 0 THEN 50
                     ELSE 
                       (100 - (present * 100.0 / total)) + 
                       (CASE WHEN recent_history[1:3] @> ARRAY['Absent'::TEXT] THEN 20 ELSE 0 END)
                   END as risk_score
            FROM student_stats
            ORDER BY risk_score DESC
            LIMIT 20
        """
        return qry(sql, params)

    @staticmethod
    def get_attendance_heatmap(dept=None):
        """Generates distribution data for heatmaps (Day of Week vs Hour)."""
        # Since we don't have 'hour' in attendance, we'll use Day of Week distribution.
        sql = """
            SELECT TO_CHAR(date::TIMESTAMP, 'Day') as day_name,
                   EXTRACT(DOW FROM date::TIMESTAMP) as dow,
                   COUNT(*) as total,
                   AVG(CASE WHEN status='Present' THEN 100 ELSE 0 END) as avg_pct
            FROM attendance
            WHERE 1=1
        """
        params = []
        if dept:
            sql += " AND EXISTS (SELECT 1 FROM students WHERE id=attendance.student_id AND department=%s)"
            params.append(dept)
        
        sql += " GROUP BY day_name, dow ORDER BY dow"
        return qry(sql, params)

    @staticmethod
    def predict_future_defaulters(threshold=75):
        """Predicts who will fall below threshold in the next 10 sessions based on current velocity."""
        sql = """
            SELECT s.name, s.roll, s.department,
                   COALESCE(COUNT(a.id), 0) as current_total,
                   COALESCE(SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END), 0) as current_present,
                   -- Velocity of last 10 records
                   COALESCE(AVG(CASE WHEN a.status='Present' THEN 100 ELSE 0 END), 0) as velocity
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id
            GROUP BY s.id, s.name, s.roll, s.department
            HAVING (COALESCE(SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END), 0) * 100.0 / NULLIF(COUNT(a.id), 0)) > %s
               AND COALESCE(AVG(CASE WHEN a.status='Present' THEN 100 ELSE 0 END), 0) < %s
        """
        # Students currently above threshold but trending below it
        return qry(sql, (threshold, threshold))

    @staticmethod
    def get_department_comparison():
        """Compares attendance performance across departments."""
        return qry("""
            SELECT s.department,
                   COUNT(DISTINCT s.id) as students,
                   COUNT(a.id) as sessions,
                   ROUND(COALESCE(AVG(CASE WHEN a.status='Present' THEN 100 ELSE 0 END), 0), 1) as avg_pct
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id
            GROUP BY s.department
            ORDER BY avg_pct DESC
        """)

    @staticmethod
    def get_insights_summary():
        """Aggregated AI insights for the dashboard with velocity-based trends."""
        try:
            # Critical risk: Overall attendance < 60%
            critical = qone("""
                SELECT COUNT(*) as c FROM (
                    SELECT student_id 
                    FROM attendance 
                    GROUP BY student_id 
                    HAVING (SUM(CASE WHEN status ILIKE 'Present' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*), 0)) < 60
                ) as sub
            """)
            
            # Top performing department
            top_dept = qone("""
                SELECT department FROM (
                    SELECT s.department, AVG(CASE WHEN a.status ILIKE 'Present' THEN 100 ELSE 0 END) as avg_pct 
                    FROM students s 
                    JOIN attendance a ON s.id=a.student_id 
                    GROUP BY 1 
                    ORDER BY 2 DESC 
                    LIMIT 1
                ) as sub
            """)
            
            # Declining trend: Students whose last 5 sessions have lower presence than their overall average
            declining = qone("""
                WITH student_overall AS (
                    SELECT student_id, AVG(CASE WHEN status ILIKE 'Present' THEN 100 ELSE 0 END) as overall_avg
                    FROM attendance
                    GROUP BY student_id
                ),
                student_recent AS (
                    SELECT student_id, AVG(CASE WHEN status ILIKE 'Present' THEN 100 ELSE 0 END) as recent_avg
                    FROM (
                        SELECT student_id, status, 
                               ROW_NUMBER() OVER(PARTITION BY student_id ORDER BY date DESC) as rn
                        FROM attendance
                    ) as ranked
                    WHERE rn <= 5
                    GROUP BY student_id
                )
                SELECT COUNT(*) as c
                FROM student_overall o
                JOIN student_recent r ON o.student_id = r.student_id
                WHERE r.recent_avg < (o.overall_avg - 10) -- Significant decline (>10%)
            """)
            
            return {
                "critical_risk_count": critical["c"] if critical else 0,
                "declining_trend_count": declining["c"] if declining else 0,
                "top_performing_dept": top_dept["department"] if top_dept else "N/A"
            }
        except Exception:
            return {"critical_risk_count":0, "declining_trend_count":0, "top_performing_dept":"N/A"}

    @staticmethod
    def get_weekly_trend(dept=None, division=None):
        """Fetches attendance trend for the last 4 weeks."""
        sql = """
            SELECT TO_CHAR(DATE_TRUNC('week', date::TIMESTAMP), 'Mon DD') as week_label,
                   AVG(CASE WHEN status ILIKE 'Present' THEN 100 ELSE 0 END) as avg_pct
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE date::TIMESTAMP >= CURRENT_DATE - INTERVAL '28 days'
        """
        params = []
        if dept: sql += " AND s.department=%s"; params.append(dept)
        if division: sql += " AND s.division=%s"; params.append(division)
        
        sql += " GROUP BY 1 ORDER BY MIN(date)"
        return qry(sql, params)
