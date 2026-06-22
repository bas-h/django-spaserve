import { useEffect, useState } from "react";
import { Link, Route, Routes, useLocation } from "react-router-dom";

function Nav() {
  return (
    <nav style={{ display: "flex", gap: 12, marginBottom: 24 }}>
      <Link to="/">Home</Link>
      <Link to="/about">About</Link>
      <Link to="/dashboard/settings">Dashboard ▸ Settings</Link>
      <Link to="/does-not-exist">Broken link</Link>
    </nav>
  );
}

function ApiProbe() {
  const [state, setState] = useState("loading…");
  useEffect(() => {
    fetch("/api/ping")
      .then((r) => r.json())
      .then((d) => setState(d.message))
      .catch((e) => setState("error: " + e));
  }, []);
  return (
    <p>
      <strong>/api/ping says:</strong> <code>{state}</code>
    </p>
  );
}

function Page({ title, children }) {
  const { pathname } = useLocation();
  return (
    <section>
      <h1>{title}</h1>
      <p>
        Rendered client-side at <code>{pathname}</code>. Reload this URL — the
        server returns <code>index.html</code> and the router takes over.
      </p>
      {children}
    </section>
  );
}

export default function App() {
  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "2rem auto", maxWidth: 640 }}>
      <Nav />
      <Routes>
        <Route path="/" element={<Page title="Home"><ApiProbe /></Page>} />
        <Route path="/about" element={<Page title="About" />} />
        <Route path="/dashboard/*" element={<Page title="Dashboard" />} />
        <Route path="*" element={<Page title="Client-side 404" />} />
      </Routes>
    </main>
  );
}
