/** Tickets list page with filtering, search, and pagination. */

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Plus, Search, Filter, ChevronLeft, ChevronRight } from "lucide-react";
import { ticketService, type TicketFilters } from "@/services/tickets";
import { cn } from "@/lib/utils";
import type { TicketPriority, TicketStatus } from "@/types";
import { formatDistanceToNow } from "date-fns";

const priorityColors: Record<TicketPriority, string> = {
  low: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  medium: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  high: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  critical: "bg-red-500/10 text-red-500 border-red-500/20",
};

const statusColors: Record<TicketStatus, string> = {
  open: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  in_progress: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  waiting_on_customer: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  waiting_on_team: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  escalated: "bg-red-500/10 text-red-400 border-red-500/20",
  resolved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  closed: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

export function TicketsPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<TicketFilters>({
    page: 1, page_size: 20, sort_by: "created_at", sort_order: "desc",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["tickets", filters],
    queryFn: () => ticketService.list(filters),
  });

  const updateFilter = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined, page: 1 }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Tickets</h1>
          <p className="mt-1 text-sm text-muted-foreground">{data?.total ?? 0} total</p>
        </div>
        <Link to="/tickets/new" className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors">
          <Plus className="h-4 w-4" /> New Ticket
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input type="text" placeholder="Search tickets..." value={filters.search || ""}
            onChange={(e) => updateFilter("search", e.target.value)}
            className="w-full rounded-lg border border-input bg-card pl-10 pr-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all" />
        </div>
        {[
          { key: "status", label: "All Status", options: ["open", "in_progress", "resolved", "closed", "escalated"] },
          { key: "priority", label: "All Priority", options: ["critical", "high", "medium", "low"] },
          { key: "category", label: "All Categories", options: ["billing", "technical", "bug", "feature_request", "security", "account", "refund", "general_inquiry"] },
        ].map((f) => (
          <select key={f.key} value={(filters as any)[f.key] || ""} onChange={(e) => updateFilter(f.key, e.target.value)}
            className="rounded-lg border border-input bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none">
            <option value="">{f.label}</option>
            {f.options.map((o) => <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
          </select>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {isLoading ? (
          <div className="p-8 space-y-4">{[...Array(5)].map((_, i) => <div key={i} className="skeleton h-16 rounded-lg" />)}</div>
        ) : !data?.items.length ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Filter className="h-10 w-10 mb-3 opacity-50" /><p className="text-sm">No tickets found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                {["Ticket", "Status", "Priority", "Category", "Assigned", "Created"].map((h, i) => (
                  <th key={h} className={cn("px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider",
                    i >= 3 && "hidden md:table-cell", i === 5 && "hidden sm:table-cell")}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.items.map((ticket, i) => (
                <motion.tr key={ticket.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}
                  onClick={() => navigate(`/tickets/${ticket.id}`)} className="cursor-pointer hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-foreground line-clamp-1">{ticket.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{ticket.ticket_number}{ticket.customer && ` · ${ticket.customer.full_name}`}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn("inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize", statusColors[ticket.status])}>
                      {ticket.status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn("inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize", priorityColors[ticket.priority])}>
                      {ticket.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className="text-xs text-muted-foreground capitalize">{ticket.category?.replace(/_/g, " ") || "—"}</span>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className="text-xs text-muted-foreground">{ticket.assigned_agent?.full_name || "Unassigned"}</span>
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <span className="text-xs text-muted-foreground">{formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}</span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}

        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between border-t border-border px-4 py-3">
            <p className="text-xs text-muted-foreground">Page {data.page} of {data.total_pages}</p>
            <div className="flex gap-2">
              <button onClick={() => setFilters((p) => ({ ...p, page: Math.max(1, (p.page || 1) - 1) }))}
                disabled={data.page <= 1} className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent disabled:opacity-50">
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button onClick={() => setFilters((p) => ({ ...p, page: Math.min(data.total_pages, (p.page || 1) + 1) }))}
                disabled={data.page >= data.total_pages} className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent disabled:opacity-50">
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
