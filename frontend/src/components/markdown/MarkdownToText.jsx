import React from "react";

export const MarkdownToText = ({ reportText }) => {
  // Utility to parse the raw text into structured objects

  console.log({ reportText });
  const parseReport = (text) => {
    if (!text) return [];

    // Split by double newline to separate major sections
    return text.split(/\n\n/).map((section, index) => {
      // Regex to capture: **Title** - Body
      const match = section.match(/^\*\*(.*?)\*\*\s*[–|-]?\s*([\s\S]*)/);

      if (!match) return { id: index, type: "plain", content: section };

      return {
        id: index,
        type: "section",
        title: match[1].trim(),
        body: match[2].trim(),
      };
    });
  };

  const sections = parseReport(reportText);

  // Helper to highlight inline elements (metrics, signals, etc.)
  const formatBody = (body) => {
    // 1. Handle Signal names (*signal_name*)
    // 2. Handle Metrics (89.87/100, 85-90%)
    // 3. Handle Amounts ($9,850)
    const parts = body.split(/(\*.*?\*|\d+\.?\d*\/100|\d+-\d+ %|\$\d+,?\d*)/g);

    return parts.map((part, i) => {
      if (part.startsWith("*") && part.endsWith("*")) {
        return (
          <code key={i} style={styles.signal}>
            {part.replaceAll("*", "")}
          </code>
        );
      }
      if (part.includes("/100") || part.includes("%")) {
        return (
          <span key={i} style={styles.metric}>
            {part}
          </span>
        );
      }
      if (part.startsWith("$")) {
        return (
          <b key={i} style={styles.amount}>
            {part}
          </b>
        );
      }
      return part;
    });
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <span style={{ marginRight: "10px" }}>🛡️</span>
        Investigation Analysis
      </header>

      {sections.map((section) => (
        <div key={section.id} style={styles.card}>
          <h3 style={styles.title}>{section.title}</h3>
          <p style={styles.body}>
            {section.type === "section"
              ? formatBody(section.body)
              : section.content}
          </p>
        </div>
      ))}
    </div>
  );
};

export default MarkdownToText;

// Vanilla CSS-in-JS object
const styles = {
  container: {
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    maxWidth: "800px",
    margin: "20px auto",
    color: "#1a202c",
    lineHeight: "1.6",
  },
  header: {
    fontSize: "0.9rem",
    fontWeight: "bold",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: "#718096",
    marginBottom: "16px",
    paddingLeft: "4px",
  },
  card: {
    backgroundColor: "#fff",
    borderLeft: "4px solid #3182ce",
    borderRadius: "4px",
    padding: "20px",
    marginBottom: "16px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)",
  },
  title: {
    margin: "0 0 12px 0",
    fontSize: "1.1rem",
    color: "#2d3748",
  },
  body: {
    margin: 0,
    fontSize: "0.95rem",
    color: "#4a5568",
  },
  signal: {
    backgroundColor: "#edf2f7",
    color: "#2d3748",
    padding: "2px 6px",
    borderRadius: "4px",
    fontSize: "0.85rem",
    fontFamily: "monospace",
    fontWeight: "bold",
  },
  metric: {
    color: "#e53e3e",
    fontWeight: "700",
  },
  amount: {
    color: "#2c5282",
  },
};
