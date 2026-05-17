/** Auth-related API calls. */

import api from "./api";
import type { TokenResponse, User } from "@/types";

export const authService = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>("/auth/login", { email, password });
    return data;
  },

  register: async (email: string, password: string, full_name: string): Promise<User> => {
    const { data } = await api.post<User>("/auth/register", { email, password, full_name });
    return data;
  },

  getMe: async (): Promise<User> => {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },

  refresh: async (refresh_token: string): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>("/auth/refresh", { refresh_token });
    return data;
  },
};
