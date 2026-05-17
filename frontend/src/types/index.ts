/** Shared TypeScript types for the frontend. */

export type UserRole = "admin" | "support_manager" | "support_agent" | "customer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  avatar_url?: string;
  phone?: string;
  department?: string;
  customer_tier?: string;
  created_at: string;
  updated_at: string;
}

export type TicketStatus =
  | "open"
  | "in_progress"
  | "waiting_on_customer"
  | "waiting_on_team"
  | "escalated"
  | "resolved"
  | "closed";

export type TicketCategory =
  | "billing"
  | "technical"
  | "bug"
  | "feature_request"
  | "security"
  | "account"
  | "refund"
  | "general_inquiry";

export type TicketPriority = "low" | "medium" | "high" | "critical";

export interface Team {
  id: string;
  name: string;
  slug: string;
  description?: string;
  is_active: boolean;
  color?: string;
  created_at: string;
}

export interface Ticket {
  id: string;
  ticket_number: string;
  title: string;
  description: string;
  category?: TicketCategory;
  predicted_category?: TicketCategory;
  category_confidence?: number;
  priority: TicketPriority;
  predicted_priority?: TicketPriority;
  priority_confidence?: number;
  status: TicketStatus;
  customer?: User;
  assigned_team?: Team;
  assigned_agent?: User;
  tags?: string[];
  source?: string;
  sentiment_score?: number;
  sentiment_label?: string;
  ai_summary?: string;
  ai_response?: string;
  ai_confidence?: number;
  is_triaged: boolean;
  first_response_at?: string;
  resolved_at?: string;
  sla_breach_at?: string;
  comments: Comment[];
  attachments: Attachment[];
  created_at: string;
  updated_at: string;
}

export interface TicketListItem {
  id: string;
  ticket_number: string;
  title: string;
  category?: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  customer?: User;
  assigned_agent?: User;
  assigned_team?: Team;
  is_triaged: boolean;
  sentiment_label?: string;
  created_at: string;
  updated_at: string;
}

export interface Comment {
  id: string;
  ticket_id: string;
  user?: User;
  content: string;
  is_internal: boolean;
  is_ai_generated: boolean;
  created_at: string;
}

export interface Attachment {
  id: string;
  ticket_id: string;
  filename: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface Activity {
  id: string;
  ticket_id: string;
  user?: User;
  action: string;
  field_name?: string;
  old_value?: string;
  new_value?: string;
  metadata_json?: Record<string, unknown>;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AnalyticsOverview {
  total_tickets: number;
  open_tickets: number;
  resolved_tickets: number;
  avg_resolution_time_hours?: number;
  avg_first_response_time_hours?: number;
  tickets_by_status: Record<string, number>;
}

export interface SimilarTicket {
  ticket: TicketListItem;
  similarity_score: number;
}
