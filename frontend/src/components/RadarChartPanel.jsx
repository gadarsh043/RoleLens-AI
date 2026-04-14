import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

const LABELS = [
  ["skills", "Skills"],
  ["experience", "Experience"],
  ["education", "Education"],
  ["culture", "Culture"],
  ["keywords", "Keywords"],
  ["seniority_match", "Seniority"],
];

export default function RadarChartPanel({ radar = {} }) {
  const data = LABELS.map(([key, label]) => ({
    metric: label,
    score: radar[key] ?? 0,
    target: 100,
  }));

  return (
    <section className="metric-card chart-card">
      <p className="panel-label">Radar View</p>
      <h3>Profile vs role requirements</h3>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={data}>
            <PolarGrid stroke="rgba(255,255,255,0.15)" />
            <PolarAngleAxis dataKey="metric" tick={{ fill: "rgba(247, 241, 232, 0.75)", fontSize: 12 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar
              dataKey="target"
              stroke="rgba(242,204,143,0.35)"
              fill="rgba(242,204,143,0.08)"
              fillOpacity={1}
            />
            <Radar
              dataKey="score"
              stroke="#ef8354"
              fill="rgba(239,131,84,0.45)"
              fillOpacity={0.7}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
