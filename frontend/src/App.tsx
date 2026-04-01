import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import ComparePage from "./pages/ComparePage";
import McDetailPage from "./pages/McDetailPage";
import McListPage from "./pages/McListPage";
import RunDetailPage from "./pages/RunDetailPage";
import RunsListPage from "./pages/RunsListPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/runs" replace />} />
        <Route path="/runs" element={<RunsListPage />} />
        <Route path="/runs/:id" element={<RunDetailPage />} />
        <Route path="/mc" element={<McListPage />} />
        <Route path="/mc/:id" element={<McDetailPage />} />
        <Route path="/compare" element={<ComparePage />} />
      </Route>
    </Routes>
  );
}
