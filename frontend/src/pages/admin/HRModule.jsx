import React from 'react';
import { Layout } from '../../components/Layout';
import { Landmark, ClipboardCheck, Briefcase } from 'lucide-react';

export const HRModule = () => {
  return (
    <Layout title="Human Resources Desk" role="admin">
      <div className="flex flex-col gap-6">
        <div className="glass p-6 rounded-2xl">
          <h2 className="text-xl font-bold text-white mb-2">Faculty HR & Payroll Records</h2>
          <p className="text-slate-400 text-sm">Configure base salaries, print payslips, and review leave requests.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass p-6 rounded-2xl flex flex-col gap-3">
            <Landmark className="h-8 w-8 text-purple-400" />
            <h3 className="text-lg font-bold text-slate-100">Payroll Statistics</h3>
            <p className="text-sm text-slate-400">View faculty base salaries, allowances, and provident fund deductions.</p>
            <button className="w-full mt-2 py-2 bg-slate-900 hover:bg-slate-800 border border-white/5 rounded-xl text-xs font-semibold text-slate-300 transition">
              Launch Registry
            </button>
          </div>

          <div className="glass p-6 rounded-2xl flex flex-col gap-3">
            <ClipboardCheck className="h-8 w-8 text-blue-400" />
            <h3 className="text-lg font-bold text-slate-100">Generate Payslips</h3>
            <p className="text-sm text-slate-400">Generate monthly PDF payslips and upload them directly to faculty vaults.</p>
            <button className="w-full mt-2 py-2 bg-slate-900 hover:bg-slate-800 border border-white/5 rounded-xl text-xs font-semibold text-slate-300 transition">
              Payslips Desk
            </button>
          </div>

          <div className="glass p-6 rounded-2xl flex flex-col gap-3">
            <Briefcase className="h-8 w-8 text-green-400" />
            <h3 className="text-lg font-bold text-slate-100">Leave Approvals</h3>
            <p className="text-sm text-slate-400">Approve or reject leave requests submitted by university teachers.</p>
            <button className="w-full mt-2 py-2 bg-slate-900 hover:bg-slate-800 border border-white/5 rounded-xl text-xs font-semibold text-slate-300 transition">
              Leave Ledger
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
};
