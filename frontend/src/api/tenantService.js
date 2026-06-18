import { api } from './authService';

export const tenantService = {
  getTenantInfo: async () => {
    const response = await api.get('/tenant/info');
    return response.data;
  }
};
