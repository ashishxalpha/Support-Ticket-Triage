/** Ticket-related API calls. */

import api from "./api";
import type {
  Ticket,
  TicketListItem,
  PaginatedResponse,
  Comment,
  Activity,
  SimilarTicket,
} from "@/types";

export interface TicketFilters {
  status?: string;
  category?: string;
  priority?: string;
  search?: string;
  assigned_agent_id?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
}

export const ticketService = {
  list: async (filters: TicketFilters = {}): Promise<PaginatedResponse<TicketListItem>> => {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([_, v]) => v !== undefined && v !== "")
    );
    const { data } = await api.get<PaginatedResponse<TicketListItem>>("/tickets", { params });
    return data;
  },

  get: async (id: string): Promise<Ticket> => {
    const { data } = await api.get<Ticket>(`/tickets/${id}`);
    return data;
  },

  create: async (ticket: {
    title: string;
    description: string;
    category?: string;
    priority?: string;
    tags?: string[];
  }): Promise<Ticket> => {
    const { data } = await api.post<Ticket>("/tickets", ticket);
    return data;
  },

  update: async (id: string, updates: Record<string, unknown>): Promise<Ticket> => {
    const { data } = await api.patch<Ticket>(`/tickets/${id}`, updates);
    return data;
  },

  getComments: async (id: string): Promise<Comment[]> => {
    const { data } = await api.get<Comment[]>(`/tickets/${id}/comments`);
    return data;
  },

  addComment: async (
    id: string,
    content: string,
    is_internal: boolean = false
  ): Promise<Comment> => {
    const { data } = await api.post<Comment>(`/tickets/${id}/comments`, {
      content,
      is_internal,
    });
    return data;
  },

  getActivities: async (id: string): Promise<Activity[]> => {
    const { data } = await api.get<Activity[]>(`/tickets/${id}/activities`);
    return data;
  },

  getSimilar: async (id: string): Promise<SimilarTicket[]> => {
    const { data } = await api.get<SimilarTicket[]>(`/tickets/${id}/similar`);
    return data;
  },
};
