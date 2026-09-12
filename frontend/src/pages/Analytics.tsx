import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, AnalyticsResponse } from "../api/client";

// Ordinal blue ramp, lightest-to-darkest as the funnel narrows -- the same five
// hues are reused across the funnel, activity-over-time, and source-effectiveness
// charts so "how far along the funnel" always maps to the same color everywhere
// on this page, instead of each chart inventing its own palette.
const STAGE_COLORS: Record<string, string> = {
  new_matches: "#86b6ef",
  staged: "#5598e7",
  applied: "#2a78d6",
  interview: "#1c5cab",
  offer: "#104281",
};
const NEUTRAL_BLUE = "#2a78d6";
const AXIS_COLOR = "#898781";
const GRID_COLOR = "#e1e0d9";
const TOOLTIP_STYLE = { borderRadius: 8, border: `1px solid ${GRID_COLOR}`, fontSize: 13 };

const PRESETS: { label: string; days: number | null }[] = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
  { label: "All time", days: null },
];

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

function formatPercent(value: number | null): string {
  if (value === null) return "-";
  return `${Math.round(value * 100)}%`;
}

function formatAxisDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePreset, setActivePreset] = useState<number | null>(30);
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [useCustom, setUseCustom] = useState(false);

  const { startDate, endDate } = useMemo(() => {
    if (useCustom) {
      return {
        startDate: customStart ? new Date(customStart).toISOString() : undefined,
        endDate: customEnd ? new Date(`${customEnd}T23:59:59`).toISOString() : undefined,
      };
    }
    return {
      startDate: activePreset !== null ? isoDaysAgo(activePreset) : undefined,
      endDate: undefined,
    };
  }, [useCustom, customStart, customEnd, activePreset]);

  useEffect(() => {
    api
      .getAnalytics(startDate, endDate)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [startDate, endDate]);

  const selectPreset = (days: number | null) => {
    setUseCustom(false);
    setActivePreset(days);
  };

  const funnelChartData = data
    ? [
        { stage: "New matches", count: data.funnel.new_matches, key: "new_matches" },
        { stage: "Staged", count: data.funnel.staged, key: "staged" },
        { stage: "Applied", count: data.funnel.applied, key: "applied" },
        { stage: "Interview", count: data.funnel.interview, key: "interview" },
        { stage: "Offer", count: data.funnel.offer, key: "offer" },
      ]
    : [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Analytics</h1>
          <div className="page-subtitle">
            {data?.range.start ? `Since ${new Date(data.range.start).toLocaleDateString()}` : "All time"}
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="filter-bar">
        <div className="filter-field">
          <label>Date range</label>
          <div className="date-preset-row">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                type="button"
                className={`date-preset-btn${!useCustom && activePreset === p.days ? " active" : ""}`}
                onClick={() => selectPreset(p.days)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
        <div className="filter-field">
          <label htmlFor="custom-start">Custom range</label>
          <div className="flex items-center gap-2">
            <input
              id="custom-start"
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
            />
            <span className="page-subtitle">to</span>
            <input
              id="custom-end"
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
            />
            <button
              className="btn btn-secondary btn-small"
              disabled={!customStart}
              onClick={() => setUseCustom(true)}
            >
              Apply
            </button>
          </div>
        </div>
      </div>

      {!data ? (
        <div className="empty-state">Nothing to show yet.</div>
      ) : (
        <>
          <div className="stat-tile-grid">
            <div className="stat-tile">
              <div className="stat-tile-label">New matches</div>
              <div className="stat-tile-value">{data.funnel.new_matches}</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Staged</div>
              <div className="stat-tile-value">{data.funnel.staged}</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Applied</div>
              <div className="stat-tile-value">{data.funnel.applied}</div>
              <div className="stat-tile-sub">{formatPercent(data.conversion_rates.staged_to_applied)} of staged</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Interviews</div>
              <div className="stat-tile-value text-emerald-600">{data.funnel.interview}</div>
              <div className="stat-tile-sub">
                {formatPercent(data.conversion_rates.applied_to_interview)} of applied
              </div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Offers</div>
              <div className="stat-tile-value text-emerald-600">{data.funnel.offer}</div>
              <div className="stat-tile-sub">
                {formatPercent(data.conversion_rates.interview_to_offer)} of interviews
              </div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Rejected</div>
              <div className="stat-tile-value text-red-600">{data.funnel.rejected}</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Withdrawn</div>
              <div className="stat-tile-value">{data.funnel.withdrawn}</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Viewed (ack.)</div>
              <div className="stat-tile-value">{data.funnel.viewed}</div>
            </div>
          </div>

          <div className="chart-card">
            <div className="chart-card-title">Funnel</div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={funnelChartData} layout="vertical" margin={{ left: 16, right: 24 }}>
                <CartesianGrid stroke={GRID_COLOR} horizontal={false} />
                <XAxis type="number" stroke={AXIS_COLOR} fontSize={12} allowDecimals={false} />
                <YAxis type="category" dataKey="stage" stroke={AXIS_COLOR} fontSize={12} width={90} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {funnelChartData.map((entry) => (
                    <Cell key={entry.key} fill={STAGE_COLORS[entry.key]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-card">
            <div className="chart-card-title">Activity over time</div>
            {data.activity_over_time.length === 0 ? (
              <div className="empty-state">No activity in this range.</div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={data.activity_over_time} margin={{ left: 8, right: 16 }}>
                  <CartesianGrid stroke={GRID_COLOR} vertical={false} />
                  <XAxis dataKey="date" stroke={AXIS_COLOR} fontSize={12} tickFormatter={formatAxisDate} />
                  <YAxis stroke={AXIS_COLOR} fontSize={12} allowDecimals={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => new Date(d).toLocaleDateString()} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line
                    type="monotone"
                    dataKey="new_matches"
                    name="New matches"
                    stroke={STAGE_COLORS.new_matches}
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="staged"
                    name="Staged"
                    stroke={STAGE_COLORS.staged}
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="applied"
                    name="Applied"
                    stroke={STAGE_COLORS.applied}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="chart-card">
            <div className="chart-card-title">Source effectiveness</div>
            {data.source_effectiveness.length === 0 ? (
              <div className="empty-state">No sourced postings in this range.</div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data.source_effectiveness} margin={{ left: 8, right: 16, bottom: 24 }}>
                  <CartesianGrid stroke={GRID_COLOR} vertical={false} />
                  <XAxis
                    dataKey="source"
                    stroke={AXIS_COLOR}
                    fontSize={11}
                    angle={-20}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis stroke={AXIS_COLOR} fontSize={12} allowDecimals={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="matches" name="Matches" fill={STAGE_COLORS.new_matches} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="staged" name="Staged" fill={STAGE_COLORS.staged} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="applied" name="Applied" fill={STAGE_COLORS.applied} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="interview" name="Interview" fill={STAGE_COLORS.interview} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="offer" name="Offer" fill={STAGE_COLORS.offer} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="chart-grid-2">
            <div className="chart-card">
              <div className="chart-card-title">Match score distribution</div>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={data.match_score_distribution}>
                  <CartesianGrid stroke={GRID_COLOR} vertical={false} />
                  <XAxis dataKey="bucket" stroke={AXIS_COLOR} fontSize={11} />
                  <YAxis stroke={AXIS_COLOR} fontSize={12} allowDecimals={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" fill={NEUTRAL_BLUE} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="chart-card">
              <div className="chart-card-title">Top matched keywords</div>
              {data.top_keywords.length === 0 ? (
                <div className="empty-state">No matched keywords in this range.</div>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={data.top_keywords} layout="vertical" margin={{ left: 16, right: 24 }}>
                    <CartesianGrid stroke={GRID_COLOR} horizontal={false} />
                    <XAxis type="number" stroke={AXIS_COLOR} fontSize={12} allowDecimals={false} />
                    <YAxis type="category" dataKey="keyword" stroke={AXIS_COLOR} fontSize={11} width={100} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Bar dataKey="count" fill={NEUTRAL_BLUE} radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
