/** Ticket detail page with AI insights, comments, and activity. */

import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useState } from "react";
import {
  ArrowLeft, Brain, MessageSquare, Send, Sparkles, Clock, User,
  Tag, AlertCircle,
} from "lucide-react";
import { ticketService } from "@/services/tickets";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";

const priorityColors: Record<string, string> = {
  low: "bg-emerald-500/10 text-emerald-500",
  medium: "bg-amber-500/10 text-amber-500",
  high: "bg-orange-500/10 text-orange-500",
  critical: "bg-red-500/10 text-red-500",
};

const statusColors: Record<string, string> = {
  open: "bg-blue-500/10 text-blue-400",
  in_progress: "bg-violet-500/10 text-violet-400",
  resolved: "bg-emerald-500/10 text-emerald-400",
  closed: "bg-gray-500/10 text-gray-400",
  escalated: "bg-red-500/10 text-red-400",
  waiting_on_customer: "bg-amber-500/10 text-amber-400",
  waiting_on_team: "bg-orange-500/10 text-orange-400",
};

export function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [comment, setComment] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [copilotSuggestion, setCopilotSuggestion] = useState<string | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    if (user?.role === "customer" || !id) return;
    const token = localStorage.getItem("access_token");
    if (!token) return;
    
    const wsUrl = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
    const socket = new WebSocket(`${wsUrl}/api/v1/ws?token=${token}`);
    
    socket.onopen = () => {
      socket.send(JSON.stringify({ action: "subscribe_ticket", ticket_id: id }));
    };
    
    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "copilot_suggestion") {
          setCopilotSuggestion(msg.data?.suggestion);
        }
      } catch (e) {
        console.error(e);
      }
    };
    
    setWs(socket);
    return () => socket.close();
  }, [id, user]);

  const handleCommentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setComment(val);
    
    // Trigger suggestion when user pauses after typing a word (ends with space)
    if (ws && val.length > 5 && val.endsWith(" ")) {
      ws.send(JSON.stringify({
        action: "copilot_suggest",
        ticket_id: id,
        content: val
      }));
    }
  };

  const { data: ticket, isLoading } = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => ticketService.get(id!),
    enabled: !!id,
  });

  const { data: similar } = useQuery({
    queryKey: ["ticket", id, "similar"],
    queryFn: () => ticketService.getSimilar(id!),
    enabled: !!id && user?.role !== "customer",
  });

  const commentMutation = useMutation({
    mutationFn: () => ticketService.addComment(id!, comment, isInternal),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      setComment("");
      toast.success("Comment added");
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => ticketService.update(id!, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      toast.success("Status updated");
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-8 w-48 rounded" />
        <div className="skeleton h-64 rounded-xl" />
      </div>
    );
  }

  if (!ticket) return <div>Ticket not found</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => navigate("/tickets")}
            className="mb-3 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Tickets
          </button>
          <div className="flex items-center gap-3">
            <span className="text-sm font-mono text-muted-foreground">{ticket.ticket_number}</span>
            <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", statusColors[ticket.status] || "")}>
              {ticket.status.replace(/_/g, " ")}
            </span>
            <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", priorityColors[ticket.priority] || "")}>
              {ticket.priority}
            </span>
          </div>
          <h1 className="mt-2 text-xl font-bold text-foreground">{ticket.title}</h1>
        </div>
        {user?.role !== "customer" && (
          <select
            value={ticket.status}
            onChange={(e) => statusMutation.mutate(e.target.value)}
            className="rounded-lg border border-input bg-card px-3 py-2 text-sm text-foreground"
          >
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="waiting_on_customer">Waiting on Customer</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
            <option value="escalated">Escalated</option>
          </select>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-xl border border-border bg-card p-5">
            <h3 className="mb-3 text-sm font-semibold text-foreground">Description</h3>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{ticket.description}</p>
            {ticket.tags && ticket.tags.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {ticket.tags.map((tag) => (
                  <span key={tag} className="flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">
                    <Tag className="h-3 w-3" />{tag}
                  </span>
                ))}
              </div>
            )}
          </motion.div>

          {/* AI Insights */}
          {ticket.is_triaged && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              className="rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-transparent p-5"
            >
              <div className="flex items-center gap-2 mb-4">
                <Brain className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-foreground">AI Triage Insights</h3>
                {ticket.ai_confidence && (
                  <span className="ml-auto text-xs text-muted-foreground">
                    Confidence: {Math.round(ticket.ai_confidence * 100)}%
                  </span>
                )}
              </div>
              {ticket.ai_summary && (
                <div className="mb-4">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Summary</p>
                  <p className="text-sm text-foreground">{ticket.ai_summary}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4 text-sm">
                {ticket.predicted_category && (
                  <div>
                    <p className="text-xs text-muted-foreground">Predicted Category</p>
                    <p className="font-medium text-foreground capitalize">{ticket.predicted_category.replace(/_/g, " ")}</p>
                    {ticket.category_confidence && <p className="text-xs text-primary">{Math.round(ticket.category_confidence * 100)}% confident</p>}
                  </div>
                )}
                {ticket.sentiment_label && (
                  <div>
                    <p className="text-xs text-muted-foreground">Sentiment</p>
                    <p className="font-medium text-foreground capitalize">{ticket.sentiment_label.replace(/_/g, " ")}</p>
                  </div>
                )}
              </div>
              {ticket.ai_response && (
                <div className="mt-4 rounded-lg border border-primary/10 bg-primary/5 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <p className="text-xs font-medium text-primary">AI Suggested Response</p>
                  </div>
                  <p className="text-sm text-foreground whitespace-pre-wrap">{ticket.ai_response}</p>
                </div>
              )}
            </motion.div>
          )}

          {/* Comments */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
              <MessageSquare className="h-4 w-4" /> Comments ({ticket.comments.length})
            </h3>
            <div className="space-y-4">
              {ticket.comments.map((c) => (
                <div key={c.id} className={cn("rounded-lg p-4", c.is_internal ? "bg-amber-500/5 border border-amber-500/10" : "bg-muted/50")}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-full bg-primary/20 flex items-center justify-center">
                        <span className="text-[10px] font-semibold text-primary">{c.user?.full_name?.charAt(0) || "?"}</span>
                      </div>
                      <span className="text-xs font-medium text-foreground">{c.user?.full_name || "System"}</span>
                      {c.is_internal && <span className="text-[10px] bg-amber-500/10 text-amber-500 px-1.5 py-0.5 rounded">Internal</span>}
                      {c.is_ai_generated && <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded">AI</span>}
                    </div>
                    <span className="text-xs text-muted-foreground">{formatDistanceToNow(new Date(c.created_at), { addSuffix: true })}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{c.content}</p>
                </div>
              ))}
            </div>

            {/* Add Comment */}
            <div className="mt-4 border-t border-border pt-4">
              <div className="relative">
                <textarea
                  value={comment}
                  onChange={handleCommentChange}
                  placeholder="Add a comment..."
                  rows={3}
                  className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all resize-none"
                />
                {copilotSuggestion && (
                  <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}
                    className="absolute bottom-full left-0 mb-2 w-full rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-foreground shadow-sm backdrop-blur-sm"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="flex items-center gap-1.5 text-xs font-semibold text-primary">
                        <Sparkles className="h-3.5 w-3.5" /> Copilot Suggestion
                      </span>
                      <button onClick={() => { setComment(comment + copilotSuggestion.replace(comment.trim(), "").trim()); setCopilotSuggestion(null); }} className="text-xs font-medium text-primary hover:underline">Accept</button>
                    </div>
                    <p className="text-muted-foreground">{copilotSuggestion}</p>
                  </motion.div>
                )}
              </div>
              <div className="mt-2 flex items-center justify-between">
                {user?.role !== "customer" && (
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    <input
                      type="checkbox"
                      checked={isInternal}
                      onChange={(e) => setIsInternal(e.target.checked)}
                      className="rounded border-border"
                    />
                    Internal note
                  </label>
                )}
                <button
                  onClick={() => commentMutation.mutate()}
                  disabled={!comment.trim() || commentMutation.isPending}
                  className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors ml-auto"
                >
                  <Send className="h-3.5 w-3.5" /> Send
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Info Card */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-4 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">Customer</p>
              <p className="font-medium text-foreground">{ticket.customer?.full_name || "—"}</p>
              <p className="text-xs text-muted-foreground">{ticket.customer?.email}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Assigned Agent</p>
              <p className="font-medium text-foreground">{ticket.assigned_agent?.full_name || "Unassigned"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Assigned Team</p>
              <p className="font-medium text-foreground">{ticket.assigned_team?.name || "Unassigned"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Category</p>
              <p className="font-medium text-foreground capitalize">{ticket.category?.replace(/_/g, " ") || "Uncategorized"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Created</p>
              <p className="font-medium text-foreground">{formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Source</p>
              <p className="font-medium text-foreground capitalize">{ticket.source || "Web"}</p>
            </div>
          </div>

          {/* Similar Tickets */}
          {similar && similar.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h3 className="mb-3 text-sm font-semibold text-foreground flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" /> Similar Tickets
              </h3>
              <div className="space-y-3">
                {similar.map((s) => (
                  <button
                    key={s.ticket.id}
                    onClick={() => navigate(`/tickets/${s.ticket.id}`)}
                    className="block w-full text-left rounded-lg border border-border p-3 hover:bg-muted/50 transition-colors"
                  >
                    <p className="text-xs font-medium text-foreground line-clamp-1">{s.ticket.title}</p>
                    <p className="mt-1 text-xs text-primary">{Math.round(s.similarity_score * 100)}% similar</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
