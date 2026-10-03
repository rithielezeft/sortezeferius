import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import Home from "@/pages/Home";
import AdminLogin from "@/pages/AdminLogin";
import Admin from "@/pages/Admin";
import PaymentReturn from "@/pages/PaymentReturn";

const Protected = ({ children }) =>
  localStorage.getItem("sz_token") ? children : <Navigate to="/admin/login" replace />;

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/pagamento/retorno" element={<PaymentReturn />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin" element={<Protected><Admin /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster theme="dark" richColors position="top-center" />
    </div>
  );
}

export default App;
