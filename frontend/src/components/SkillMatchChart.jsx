import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis } from "recharts";

export default function SkillMatchChart({ matchedSkills = [], missingSkills = [] }) {
  const data = [
    ...matchedSkills.slice(0, 6).map((skill) => ({ name: skill, value: 100, state: "matched" })),
    ...missingSkills.slice(0, 6).map((skill) => ({ name: skill, value: 55, state: "missing" })),
  ];

  return (
    <section className="metric-card chart-card">
      <p className="panel-label">Skill Signals</p>
      <h3>Matched vs missing skills</h3>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data} layout="vertical" margin={{ left: 12, right: 12 }}>
            <XAxis type="number" hide domain={[0, 100]} />
            <YAxis
              type="category"
              dataKey="name"
              width={110}
              tick={{ fill: "rgba(247, 241, 232, 0.75)", fontSize: 12 }}
            />
            <Bar dataKey="value" radius={[0, 12, 12, 0]}>
              {data.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={entry.state === "matched" ? "rgba(120, 214, 173, 0.85)" : "rgba(239, 131, 84, 0.85)"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
