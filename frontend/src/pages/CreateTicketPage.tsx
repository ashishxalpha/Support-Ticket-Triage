/** Create ticket page with form validation. */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Send, Loader2 } from "lucide-react";
import { ticketService } from "@/services/tickets";
import { toast } from "sonner";

import { DeflectionChat } from "@/components/DeflectionChat";

export function CreateTicketPage() {
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [category, setCategory] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      ticketService.create({
        title,
        description,
        priority,
        category: category || undefined,
      }),
    onSuccess: (ticket) => {
      toast.success("Ticket created! AI triage in progress...");
      navigate(`/tickets/${ticket.id}`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || "Failed to create ticket");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim() && description.trim().length >= 10) {
      mutation.mutate();
    }
  };

  if (!showForm) {
    return (
      <div className="mx-auto max-w-2xl py-8">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="mb-6 text-2xl font-bold text-foreground">Need Help?</h1>
          <DeflectionChat onBypass={() => setShowForm(true)} />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-foreground">Create New Ticket</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Describe your issue and our AI will automatically triage it
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Brief description of your issue"
              className="w-full rounded-lg border border-input bg-card px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
              required
              maxLength={500}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide detailed information about your issue. Include error messages, steps to reproduce, and any relevant context."
              rows={8}
              className="w-full rounded-lg border border-input bg-card px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all resize-none"
              required
              minLength={10}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              {description.length}/50000 characters (minimum 10)
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Priority <span className="text-muted-foreground">(optional)</span>
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Category <span className="text-muted-foreground">(auto-detected by AI)</span>
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none"
              >
                <option value="">Let AI decide</option>
                <option value="billing">Billing</option>
                <option value="technical">Technical</option>
                <option value="bug">Bug</option>
                <option value="feature_request">Feature Request</option>
                <option value="security">Security</option>
                <option value="account">Account</option>
                <option value="refund">Refund</option>
                <option value="general_inquiry">General Inquiry</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={mutation.isPending || !title.trim() || description.length < 10}
              className="flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-all"
            >
              {mutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {mutation.isPending ? "Creating..." : "Create Ticket"}
            </button>
            <button
              type="button"
              onClick={() => navigate("/tickets")}
              className="rounded-lg border border-border px-6 py-2.5 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
