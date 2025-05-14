import { useState, useEffect } from "react";
import { api } from "../lib/api";
import ReactMarkdown from "react-markdown";

export default function ExplainPage() {
  const [input, setInput] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  // On mount, fetch the last‐built prompt and stick it in the textarea
  useEffect(() => {
    api
      .get("/explain/prompt")
      .then(({ data }) => {
        setInput(data.prompt);
      })
      .catch((err) => {
        console.error("Could not load prompt:", err);
      });
  }, []);

  async function run() {
    setLoading(true);
    setText("");

    try {
      // if user cleared out the prompt, reload the latest
      let promptText = input.trim();
      if (!promptText) {
        const { data } = await api.get("/explain/prompt");
        promptText = data.prompt;
        setInput(promptText);
      }

      // send the prompt string to /explain
      const { data: resp } = await api.post("/explain", { prompt: promptText });
      setText(resp.explanation);
    } catch (err) {
      setText("❌ " + (err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h2 className="text-xl font-semibold mb-4">Explainable AI</h2>

      <textarea
        rows={8}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        className="w-full border rounded p-2 font-mono"
      />

      <button
        onClick={run}
        disabled={loading}
        className="rounded bg-brand-blue text-white px-4 py-2 mt-2"
      >
        {loading ? "Loading…" : "Explain"}
      </button>

      {text && (
        <div className="mt-4 prose max-w-none">
          <ReactMarkdown>{text}</ReactMarkdown>
        </div>
      )}
    </>
  );
}
