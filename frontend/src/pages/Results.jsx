import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { analyzeJobDescription, chatWithResume } from "../api/client";
import ChatPanel from "../components/ChatPanel";
import FitScoreRing from "../components/FitScoreRing";
import GapAnalysis from "../components/GapAnalysis";
import RadarChartPanel from "../components/RadarChartPanel";
import SkillMatchChart from "../components/SkillMatchChart";

export default function Results() {
  const location = useLocation();
  const [payload, setPayload] = useState(location.state ?? null);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatError, setChatError] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isChatCollapsed, setIsChatCollapsed] = useState(false);

  useEffect(() => {
    if (location.state) {
      setPayload(location.state);
      setChatMessages(buildInitialMessages(location.state));
      return;
    }

    const savedPayload = sessionStorage.getItem("rolelens:last-analysis");
    if (savedPayload) {
      const parsedPayload = JSON.parse(savedPayload);
      setPayload(parsedPayload);
      setChatMessages(buildInitialMessages(parsedPayload));
    }
  }, [location.state]);

  if (!payload?.analysis) {
    return (
      <main className="page-shell">
        <section className="results-placeholder">
          <h1>No analysis yet</h1>
          <p>Run an analysis from the home page before opening the dashboard.</p>
          <Link className="text-link" to="/">
            Return home
          </Link>
        </section>
      </main>
    );
  }

  const { analysis, resume, generatedAt } = payload;

  async function handleAsk() {
    const trimmedInput = chatInput.trim();
    if (!trimmedInput) {
      setChatError("Enter a follow-up question.");
      return;
    }

    setChatError("");
    setIsChatLoading(true);

    const nextUserMessage = { role: "user", content: trimmedInput };
    const nextHistory = [...chatMessages, nextUserMessage];
    setChatMessages(nextHistory);
    setChatInput("");

    try {
      const response = await chatWithResume(trimmedInput, nextHistory);
      setChatMessages([
        ...nextHistory,
        {
          role: "assistant",
          content: response.answer,
          scope: response.scope ?? "resume",
          sourceTypes: Array.from(new Set((response.sources ?? []).map((item) => item.source_type))),
          followUpSuggestions: response.follow_up_suggestions ?? [],
        },
      ]);
    } catch (error) {
      setChatError(error.message);
      setChatMessages((currentMessages) => currentMessages.slice(0, -1));
    } finally {
      setIsChatLoading(false);
    }
  }

  async function handleReanalyze() {
    const trimmedInput = chatInput.trim();
    if (!trimmedInput) {
      setChatError("Paste a new job description to reanalyze.");
      return;
    }

    setChatError("");
    setIsChatLoading(true);

    try {
      const nextAnalysis = await analyzeJobDescription(trimmedInput);
      const nextPayload = {
        ...payload,
        analysis: nextAnalysis,
        jobDescription: trimmedInput,
        generatedAt: new Date().toISOString(),
      };
      const assistantMessage = {
        role: "assistant",
        content: nextAnalysis.summary,
        scope: "comparison",
        sourceTypes: ["resume", "job_description"],
        followUpSuggestions: nextAnalysis.recommendations?.slice(0, 3).map((item) => item.title) ?? [],
      };

      setPayload(nextPayload);
      setChatInput("");
      setChatMessages([
        ...chatMessages,
        { role: "user", content: trimmedInput },
        assistantMessage,
      ]);
      sessionStorage.setItem("rolelens:last-analysis", JSON.stringify(nextPayload));
    } catch (error) {
      setChatError(error.message);
    } finally {
      setIsChatLoading(false);
    }
  }

  function handleChatKeyDown(event) {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    event.preventDefault();
    handleAsk();
  }

  return (
    <main className="page-shell results-shell">
      <section className="results-hero">
        <div>
          <p className="eyebrow">Analysis Results</p>
          <h1>{analysis.role_detected || "Role fit summary"}</h1>
          <p className="lede">{analysis.summary}</p>
        </div>
        <div className="hero-meta">
          <p>
            Resume: <strong>{resume?.filename ?? "Indexed resume"}</strong>
          </p>
          <p>
            Seniority: <strong>{analysis.seniority}</strong>
          </p>
          <p>
            Generated: <strong>{new Date(generatedAt).toLocaleString()}</strong>
          </p>
        </div>
      </section>

      <section className="results-layout">
        <div className="results-main">
          <section className="results-grid">
            <FitScoreRing
              fitScore={analysis.fit_score}
              grade={analysis.grade}
              roleDetected={analysis.role_detected}
            />
            <section className="metric-card insight-card">
              <p className="panel-label">Cover Letter Angle</p>
              <h3>Suggested framing</h3>
              <p>{analysis.cover_letter_angle}</p>
            </section>
            <RadarChartPanel radar={analysis.radar} />
            <SkillMatchChart
              matchedSkills={analysis.matched_skills}
              missingSkills={analysis.missing_skills}
            />
            <GapAnalysis gaps={analysis.gaps} recommendations={analysis.recommendations} />
          </section>
        </div>
        <ChatPanel
          messages={chatMessages}
          inputValue={chatInput}
          onInputChange={(event) => setChatInput(event.target.value)}
          onInputKeyDown={handleChatKeyDown}
          onAsk={handleAsk}
          onReanalyze={handleReanalyze}
          isLoading={isChatLoading}
          errorMessage={chatError}
          isCollapsed={isChatCollapsed}
          onToggleCollapse={() => setIsChatCollapsed((value) => !value)}
        />
      </section>
    </main>
  );
}

function buildInitialMessages(payload) {
  if (!payload?.analysis) {
    return [];
  }

  return [
    {
      role: "assistant",
      content: payload.analysis.summary,
      scope: "comparison",
      sourceTypes: ["resume", "job_description"],
      followUpSuggestions:
        payload.analysis.recommendations?.slice(0, 3).map((item) => item.title) ?? [],
    },
  ];
}
