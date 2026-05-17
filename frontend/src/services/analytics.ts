/** Analytics API calls. */

import api from "./api";
import type { AnalyticsOverview } from "@/types";

export const analyticsService = {
  getOverview: async (): Promise<AnalyticsOverview> => {
    const { data } = await api.get<AnalyticsOverview>("/analytics/overview");
    return data;
  },

  getTicketAnalytics: async () => {
    const { data } = await api.get("/analytics/tickets");
    return data;
  },

  getSLA: async () => {
    const { data } = await api.get("/analytics/sla");
    return data;
  },

  getAgentWorkload: async () => {
    const { data } = await api.get("/analytics/agents");
    return data;
  },

  getAIPerformance: async () => {
    const { data } = await api.get("/analytics/ai-performance");
    return data;
  },
};
