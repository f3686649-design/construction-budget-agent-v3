import { useEffect, useRef, useState } from "react";
import { aiChat, generateAiConclusion, getAiConclusion, getAiStatus } from "../api/client";
import { ChartCard } from "../components/ChartCard";
import type { AiChatMessage, AiConclusion, AiStatus, GeneratedProject } from "../types";

interface AiConclusionPageProps {
  project: GeneratedProject | null;
}

const SUGGESTED_QUESTIONS = [
  "Почему проект не проходит банк?",
  "Что сильнее всего бьёт по марже?",
  "До какой цены торговаться по участку?",
  "Какие три действия сделать в первую очередь?"
];

export function AiConclusionPage({ project }: AiConclusionPageProps) {
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [conclusion, setConclusion] = useState<AiConclusion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<AiChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    getAiStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    setConclusion(null);
    setError(null);
    setMessages([]);
    setChatError(null);
    setQuestion("");
    if (project?.project_id) {
      getAiConclusion(project.project_id)
        .then(setConclusion)
        .catch(() => setConclusion(null));
    }
  }, [project?.project_id]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, chatLoading]);

  if (!project) {
    return (
      <section className="empty-state">
        <p>Создайте новый расчёт, чтобы сформировать ИИ-заключение и задать вопросы по проекту.</p>
      </section>
    );
  }

  const configured = status?.configured ?? false;

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateAiConclusion(project.project_id);
      if (result.status === "ok") {
        setConclusion(result);
      } else {
        setError(result.error ?? "Не удалось сформировать заключение.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сформировать заключение.");
    } finally {
      setLoading(false);
    }
  };

  const askQuestion = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || chatLoading) {
      return;
    }
    setChatError(null);
    const history = messages;
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setQuestion("");
    setChatLoading(true);
    try {
      const result = await aiChat(project.project_id, trimmed, history);
      if (result.status === "ok" && result.answer) {
        setMessages((current) => [...current, { role: "assistant", content: String(result.answer) }]);
      } else {
        setChatError(result.error ?? "Не удалось получить ответ.");
      }
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Не удалось получить ответ.");
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="page-stack">
      <section className="verdict-banner tone-blue">
        <span className="verdict-title">Заключение ИИ · аналитическая записка и чат</span>
        <p>
          LLM получает все цифры и вердикты модели (земля, банк, ТУ, риски), пишет жёсткую записку для
          инвестора и кредитного комитета и отвечает на вопросы по проекту.
        </p>
        <small>
          {status
            ? configured
              ? `Провайдер: ${status.provider} · модель: ${status.model}`
              : status.detail ?? "ИИ недоступен."
            : "Статус ИИ неизвестен."}
        </small>
      </section>

      <div>
        <button className="primary-button" type="button" onClick={handleGenerate} disabled={loading || !configured}>
          {loading ? "Формирую заключение…" : conclusion ? "Сформировать заново" : "Сформировать заключение"}
        </button>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      {conclusion?.conclusion ? (
        <ChartCard
          title="Аналитическая записка"
          subtitle={`Сформировано: ${conclusion.generated_at ?? "—"} · модель: ${conclusion.model ?? "—"}`}
        >
          <div className="ai-conclusion-text">{conclusion.conclusion}</div>
        </ChartCard>
      ) : null}

      <ChartCard title="Чат по проекту" subtitle="Вопросы в свободной форме — ответы только по данным модели">
        {messages.length === 0 ? (
          <div className="chat-suggestions">
            {SUGGESTED_QUESTIONS.map((item) => (
              <button
                key={item}
                className="chat-suggestion"
                type="button"
                disabled={!configured || chatLoading}
                onClick={() => askQuestion(item)}
              >
                {item}
              </button>
            ))}
          </div>
        ) : null}

        <div className="chat-thread" ref={threadRef}>
          {messages.map((message, index) => (
            <div key={index} className={`chat-bubble ${message.role}`}>
              {message.content}
            </div>
          ))}
          {chatLoading ? <div className="chat-bubble assistant muted">ИИ думает…</div> : null}
        </div>

        {chatError ? <div className="error-banner">{chatError}</div> : null}

        <form
          className="chat-input-row"
          onSubmit={(event) => {
            event.preventDefault();
            void askQuestion(question);
          }}
        >
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={configured ? "Задайте вопрос по проекту…" : "Чат недоступен: не задан OPENAI_API_KEY"}
            disabled={!configured || chatLoading}
            maxLength={2000}
          />
          <button className="primary-button" type="submit" disabled={!configured || chatLoading || !question.trim()}>
            Спросить
          </button>
        </form>
      </ChartCard>
    </div>
  );
}
