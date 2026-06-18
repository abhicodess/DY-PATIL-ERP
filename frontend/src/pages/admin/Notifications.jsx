import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Bell, Plus, MessageSquare } from 'lucide-react';

export const Notifications = () => {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [receiverRole, setReceiverRole] = useState('student');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [statusMsg, setStatusMsg] = useState('');

  // Fetch sent messages
  const { data, isLoading } = useQuery({
    queryKey: ['adminSentNotifications'],
    queryFn: async () => {
      const response = await api.get('/notifications');
      return response.data;
    },
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (payload) => {
      await api.post('/notifications', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['adminSentNotifications']);
      setStatusMsg('Notification broadcasted successfully!');
      setTimeout(() => setStatusMsg(''), 3000);
      setShowForm(false);
      setSubject('');
      setBody('');
    },
    onError: () => {
      setStatusMsg('Failed to send notification');
      setTimeout(() => setStatusMsg(''), 3000);
    },
  });

  const handleSend = (e) => {
    e.preventDefault();
    if (!subject || !body) return;
    createMutation.mutate({
      receiver_role: receiverRole,
      receiver_id: 0, // Broadcast
      subject,
      body,
    });
  };

  return (
    <Layout title="Alert Broadcast Desk" role="admin">
      <div className="flex flex-col gap-6">
        {/* Actions header */}
        <div className="glass p-6 rounded-2xl flex items-center justify-between">
          <p className="text-slate-400 text-sm">Create and broadcast global announcements to Students or Faculty.</p>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-xl transition font-semibold text-sm"
          >
            New Broadcast
          </button>
        </div>

        {statusMsg && (
          <div className="p-4 bg-green-500/10 border border-green-500/20 text-green-400 rounded-xl text-center text-sm font-semibold">
            {statusMsg}
          </div>
        )}

        {/* Modal / Dialog Form inline */}
        {showForm && (
          <div className="glass p-6 rounded-2xl border border-purple-500/20 max-w-lg">
            <h3 className="text-lg font-bold text-white mb-4">Send Broadcast Notification</h3>
            <form onSubmit={handleSend} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Target Audience</label>
                <div className="flex gap-4">
                  {['student', 'faculty'].map((t) => (
                    <label key={t} className="flex items-center gap-2 text-sm text-slate-200 capitalize cursor-pointer">
                      <input
                        type="radio"
                        name="target"
                        value={t}
                        checked={receiverRole === t}
                        onChange={() => setReceiverRole(t)}
                        className="text-purple-600 focus:ring-purple-500 bg-slate-900 border-white/10"
                      />
                      {t}s
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Subject Header</label>
                <input
                  type="text"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-200"
                  placeholder="e.g. Schedule Update"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Message Content</label>
                <textarea
                  required
                  rows={4}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-200"
                  placeholder="Type message text here..."
                />
              </div>

              <div className="flex items-center gap-2">
                <button type="submit" className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-sm font-semibold transition">
                  Send Broadcast
                </button>
                <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-semibold transition">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* List of Sent notifications */}
        <div className="glass p-6 rounded-2xl">
          <h3 className="text-xl font-bold text-white mb-4">Sent Bulletins History</h3>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2].map((n) => (
                <div key={n} className="h-16 bg-slate-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : data?.data?.length === 0 ? (
            <p className="text-slate-500">No sent bulletins found.</p>
          ) : (
            <div className="space-y-4">
              {data?.data?.map((msg) => (
                <div key={msg.id} className="p-4 bg-white/5 border border-white/5 rounded-xl">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-bold text-white text-base">{msg.subject}</h4>
                    <span className="text-xs text-slate-400">{msg.created_at}</span>
                  </div>
                  <p className="text-slate-300 text-sm mb-2">{msg.body}</p>
                  <span className="text-xs bg-slate-900 text-purple-400 border border-white/5 px-2 py-0.5 rounded font-semibold capitalize">
                    To: {msg.receiver_role}s
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};
