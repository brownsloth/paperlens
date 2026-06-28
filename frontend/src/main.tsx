import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import PublicApp from "./PublicApp";
import "./index.css";

const Root = import.meta.env.VITE_PUBLIC_MODE === "true" ? PublicApp : App;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
