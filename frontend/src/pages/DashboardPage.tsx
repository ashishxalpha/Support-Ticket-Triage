/** Dashboard page with analytics charts and overview metrics. */

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Area, AreaChart,
} from "recharts";
import {
  Ticket, Clock, CheckCircle2, AlertTriangle, TrendingUp, Brain, Users, Zap,
} from "lucide-react";
import { analyticsService } from "@/services/analytics";

const COLORS = ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#06b6d4", "#84cc16"];

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.1, duration: 0.4, ease: "easeOut" },
  }),
};

export function DashboardPage() {
  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: analyticsService.getOverview,
  });

  const { data: ticketAnalytics } = useQuery({
    queryKey: ["analytics", "tickets"],
    queryFn: analyticsService.getTicketAnalytics,
  });

  const { data: aiPerformance } = useQuery({
    queryKey: ["analytics", "ai-performance"],
    queryFn: analyticsService.getAIPerformance,
  });

  const statCards = [
    {
      label: "Total Tickets",
      value: overview?.total_tickets ?? 0,
      icon: Ticket,
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      label: "Open Tickets",
      value: overview?.open_tickets ?? 0,
      icon: AlertTriangle,
      color: "text-amber-500",
      bg: "bg-amber-500/10",
    },
    {
      label: "Resolved",
      value: overview?.resolved_tickets ?? 0,
      icon: CheckCircle2,
      color: "text-emerald-500",
      bg: "bg-emerald-500/10",
    },
    {
      label: "Avg Resolution",
      value: overview?.avg_resolution_time_hours
        ? `${overview.avg_resolution_time_hours}h`
        : "N/A",
      icon: Clock,
      color: "text-blue-500",
      bg: "bg-blue-500/10",
    },
  ];

  const categoryData = ticketAnalytics?.by_category
    ? Object.entries(ticketAnalytics.by_category).map(([name, value]) => ({
        name: name.replace("_", " "),
        value,
      }))
    : [];

  const priorityData = ticketAnalytics?.by_priority
    ? Object.entries(ticketAnalytics.by_priority).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  const dailyData = ticketAnalytics?.daily_created || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          AI triage performance and ticket analytics overview
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat, i) => (
          <motion.div
            key={stat.label}
            custom={i}
            initial="hidden"
            animate="visible"
            variants={cardVariants}
            className="rounded-xl border border-border bg-card p-5 transition-all hover:shadow-lg hover:shadow-primary/5"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <p className="mt-1 text-2xl font-bold text-foreground">
                  {loadingOverview ? (
                    <span className="skeleton inline-block h-8 w-16 rounded" />
                  ) : (
                    stat.value
                  )}
                </p>
              </div>
              <div className={`rounded-lg p-3 ${stat.bg}`}>
                <stat.icon className={`h-5 w-5 ${stat.color}`} />
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* AI Performance Banner */}
      {aiPerformance && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="rounded-xl border border-primary/20 bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 p-5"
        >
          <div className="flex items-center gap-3 mb-3">
            <Brain className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-foreground">AI Triage Performance</h3>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Tickets Triaged</p>
              <p className="text-xl font-bold text-foreground">{aiPerformance.total_triaged}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Category Accuracy</p>
              <p className="text-xl font-bold text-emerald-500">{aiPerformance.category_accuracy}%</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Priority Accuracy</p>
              <p className="text-xl font-bold text-blue-500">{aiPerformance.priority_accuracy}%</p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Category Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="rounded-xl border border-border bg-card p-5"
        >
          <h3 className="mb-4 font-semibold text-foreground">Tickets by Category</h3>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {categoryData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "hsl(222, 47%, 8%)",
                    border: "1px solid hsl(215, 28%, 17%)",
                    borderRadius: "8px",
                    color: "hsl(210, 20%, 98%)",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[280px] items-center justify-center text-muted-foreground">
              No data available
            </div>
          )}
          <div className="mt-2 flex flex-wrap gap-3">
            {categoryData.map((item, i) => (
              <div key={item.name} className="flex items-center gap-1.5 text-xs">
                <div
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="text-muted-foreground capitalize">{item.name}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Priority Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="rounded-xl border border-border bg-card p-5"
        >
          <h3 className="mb-4 font-semibold text-foreground">Tickets by Priority</h3>
          {priorityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={priorityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(215, 28%, 17%)" />
                <XAxis dataKey="name" stroke="hsl(217, 11%, 65%)" fontSize={12} />
                <YAxis stroke="hsl(217, 11%, 65%)" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: "hsl(222, 47%, 8%)",
                    border: "1px solid hsl(215, 28%, 17%)",
                    borderRadius: "8px",
                    color: "hsl(210, 20%, 98%)",
                  }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {priorityData.map((entry, i) => {
                    const colorMap: Record<string, string> = {
                      low: "#10b981",
                      medium: "#f59e0b",
                      high: "#f97316",
                      critical: "#ef4444",
                    };
                    return <Cell key={i} fill={colorMap[entry.name] || COLORS[i]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[280px] items-center justify-center text-muted-foreground">
              No data available
            </div>
          )}
        </motion.div>
      </div>

      {/* Daily Trend */}
      {dailyData.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="rounded-xl border border-border bg-card p-5"
        >
          <h3 className="mb-4 font-semibold text-foreground">Daily Ticket Volume (30 Days)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(215, 28%, 17%)" />
              <XAxis
                dataKey="date"
                stroke="hsl(217, 11%, 65%)"
                fontSize={11}
                tickFormatter={(v) => v.slice(5)}
              />
              <YAxis stroke="hsl(217, 11%, 65%)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: "hsl(222, 47%, 8%)",
                  border: "1px solid hsl(215, 28%, 17%)",
                  borderRadius: "8px",
                  color: "hsl(210, 20%, 98%)",
                }}
              />
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="count"
                stroke="#8b5cf6"
                fill="url(#colorCount)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>
      )}
    </div>
  );
}
