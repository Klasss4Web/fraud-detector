import React from "react";
import "./Toast.css";

function Toast({ message, type = "info", onClose }) {
  return (
    <div
      className={`custom-toast custom-toast-${type}`}
      style={{
        position: "fixed",
        top: 24,
        right: 24,
        zIndex: 9999,
        minWidth: 220,
        padding: "1rem 1.5rem",
        borderRadius: 8,
        background:
          type === "error"
            ? "#fff1f0"
            : type === "success"
              ? "#f6ffed"
              : "#e6f4ff",
        color:
          type === "error"
            ? "#cf1322"
            : type === "success"
              ? "#389e0d"
              : "#0958d9",
        border: `1.5px solid ${type === "error" ? "#ffa39e" : type === "success" ? "#b7eb8f" : "#91caff"}`,
        boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
        fontWeight: 500,
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}
    >
      <span style={{ flex: 1 }}>{message}</span>
      <button
        onClick={onClose}
        style={{
          background: "none",
          border: "none",
          color: "inherit",
          fontWeight: 700,
          fontSize: 18,
          cursor: "pointer",
        }}
        aria-label="Close"
      >
        ×
      </button>
    </div>
  );
}

export default Toast;
