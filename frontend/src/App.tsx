import { HashRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import Customer from "./pages/Customer";
import Analyst from "./pages/Analyst";
import CaseDetail from "./pages/CaseDetail";
import Templates from "./pages/Templates";
import BudgetLab from "./pages/BudgetLab";
import MetricsPage from "./pages/Metrics";
import Simulator from "./pages/Simulator";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Customer />} />
          <Route path="/analyst" element={<Analyst />} />
          <Route path="/case/:id" element={<CaseDetail />} />
          <Route path="/scams" element={<Templates />} />
          <Route path="/budget" element={<BudgetLab />} />
          <Route path="/metrics" element={<MetricsPage />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
