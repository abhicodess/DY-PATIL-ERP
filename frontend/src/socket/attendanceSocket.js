import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';
import { useAuthStore } from '../store/useAuthStore';

export const useAttendanceSocket = (sessionId) => {
  const [presentCount, setPresentCount] = useState(0);
  const [absentCount, setAbsentCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [isLocked, setIsLocked] = useState(false);

  useEffect(() => {
    if (!sessionId) return;

    const token = useAuthStore.getState().accessToken;
    // Connect to /attendance namespace with auth token
    const socket = io('/attendance', {
      auth: { token },
      transports: ['websocket'],
    });

    socket.on('connect', () => {
      console.log('Connected to attendance namespace room:', sessionId);
      socket.emit('join', { session_id: sessionId });
    });

    socket.on('attendance_update', (data) => {
      if (Number(data.session_id) === Number(sessionId)) {
        setPresentCount(data.present_count);
        setAbsentCount(data.absent_count);
        setTotal(data.total);
      }
    });

    socket.on('session_locked', (data) => {
      if (Number(data.session_id) === Number(sessionId)) {
        setIsLocked(true);
      }
    });

    return () => {
      socket.emit('leave', { session_id: sessionId });
      socket.disconnect();
    };
  }, [sessionId]);

  return { presentCount, absentCount, total, isLocked, setPresentCount, setAbsentCount, setTotal, setIsLocked };
};
