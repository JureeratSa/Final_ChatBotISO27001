import { useState } from 'react';

/**
 * useDashboardData — ดึงข้อมูลสถิติภาพรวม (GET /api/admin/stats) และ state ของ
 * slide-out panel "Trend Drawer" ที่เปิดจากการคลิกจุดบนกราฟแนวโน้มในหน้า Dashboard
 * (ตัวคำนวณ/render กราฟยังอยู่ใน component ของหน้า Dashboard เอง ตามแผน)
 * แยกออกมาจาก App.jsx เดิม
 */
export function useDashboardData(API_URL, fetch) {
  const [stats, setStats] = useState({
    total_documents: 0,
    active_documents: 0,
    total_queries: 0,
    likes: 0,
    dislikes: 0,
    pending_unanswered: 0,
    recent_comments: []
  });

  // Slide-out panel showing the Q&A behind a clicked point on the dashboard trend chart
  const [trendDrawer, setTrendDrawer] = useState(null); // { dateLabel, type: 'answered' | 'unanswered', items: [] }

  const fetchStats = () => {
    fetch(API_URL + '/api/admin/stats')
      .then(r => r.json())
      .then(data => {
        setStats({
          total_queries: data.total_queries || 0,
          likes: data.total_likes || 0,
          dislikes: data.total_dislikes || 0,
          pending_unanswered: data.total_unanswered || 0,
          total_documents: data.total_documents || 0,
          active_documents: data.active_documents || 0,
          queries_today: data.queries_today || 0,
          avg_response_time: data.avg_response_time || 0.0
        });
      })
      .catch(err => console.error("Error fetching stats:", err));
  };

  return {
    stats,
    setStats,
    fetchStats,
    trendDrawer,
    setTrendDrawer,
  };
}
