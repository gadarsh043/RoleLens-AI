import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

const Home = lazy(() => import("./pages/Home"));
const Results = lazy(() => import("./pages/Results"));

export default function App() {
  return (
    <Suspense fallback={<main className="page-shell">Loading...</main>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/results" element={<Results />} />
      </Routes>
    </Suspense>
  );
}
