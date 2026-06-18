import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Bell, CheckCircle } from 'lucide-react';

export const Notifications = () => {
  const queryClient = useQueryClient();

  // Fetch notifications
  const { data, isLoading } = useQuery({
    queryKey: ['studentNotifications'],
    queryFn: async () => {
      const response = await api.get('/notifications');
      return response.data;
    },
  });

  // Mark read mutation
  const readMutation = useMutation({
    mutationFn: async (id) => {
      await api.post(`/notifications/${id}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['studentNotifications']);
    },
  });

  const handleMarkRead = (id) => {
    readMutation.mutate(id);
  };

  return (
    <Layout title="Bulletin Box" role="student">
      <div className="glass p-6 rounded-2xl">
        <h3 className="text-xl font-bold text-white mb-4">Official Bulletins</h3>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2].map((n) => (
              <div key={n} className="h-16 bg-slate-800 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : data?.data?.length === 0 ? (
          <p className="text-slate-500">No active notices found in your mailbox.</p>
        ) : (
          <div className="space-y-4">
            {data?.data?.map((msg) => (
              <div
                key={msg.id}
                className={`p-4 rounded-xl border transition ${
                  msg.is_read
                    ? 'bg-white/5 border-white/5'
                    : 'bg-purple-500/5 border-purple-500/20'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-white text-base">{msg.subject}</h4>
                    {!msg.is_read && (
                      <span className="h-2 w-2 rounded-full bg-purple-500 animate-pulse" />
                    )}
                  </div>
                  <span className="text-xs text-slate-400">{msg.created_at}</span>
                </div>
                <p className="text-slate-300 text-sm mb-3">{msg.body}</p>
                
                {!msg.is_read && (
                  <button
                    onClick={() => handleMarkRead(msg.id)}
                    className="flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300 font-semibold transition"
                  >
                    <CheckCircle className="h-3.5 w-3.5" />
                    Mark as Read
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};
