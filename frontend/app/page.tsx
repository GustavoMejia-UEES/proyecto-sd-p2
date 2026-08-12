"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Task = { id: string; titulo: string; estado: string; source?: string; camera_id?: string; event_id?: string; priority?: string; created_at?: string; updated_at?: string };
type Camera = { camera_id?: string; id?: string; name?: string; location?: string; status?: string; state?: string; fps?: number; stream_url?: string; vision_mode?: string; detections?: number };
type EventItem = { id?: string; event_id?: string; camera_id?: string; type?: string; object_name?: string; description?: string; confidence?: number; created_at?: string };

const fallbackApi = "http://localhost:8000";

async function request<T>(api: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${api}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!response.ok) throw new Error((await response.text()) || `Error ${response.status}`);
  return response.status === 204 ? (undefined as T) : response.json();
}

function arrayFrom<T>(value: unknown): T[] { return Array.isArray(value) ? value : ((value as { items?: T[] })?.items || []); }

export default function Home() {
  const [api, setApi] = useState(fallbackApi);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [title, setTitle] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [status, setStatus] = useState("Pendiente");
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [health, setHealth] = useState<"checking" | "healthy" | "offline">("checking");

  const load = useCallback(async (base = api) => {
    setLoading(true); setError("");
    try {
      const [taskData, cameraData, eventData, summaryData] = await Promise.all([
        request<unknown>(base, "/api/tasks"), request<unknown>(base, "/api/cameras").catch(() => []),
        request<unknown>(base, "/api/events").catch(() => []), request<Record<string, unknown>>(base, "/api/system/summary").catch(() => null),
      ]);
      setTasks(arrayFrom<Task>(taskData)); setCameras(arrayFrom<Camera>(cameraData)); setEvents(arrayFrom<EventItem>(eventData)); setSummary(summaryData);
      await request(`${base}`, "/health"); setHealth("healthy");
    } catch (e) { setHealth("offline"); setError(e instanceof Error ? e.message : "No se pudo conectar con el backend"); }
    finally { setLoading(false); }
  }, [api]);

  useEffect(() => { fetch("/api/config").then((r) => r.json()).then((v: { apiUrl?: string }) => { const base = (v.apiUrl || fallbackApi).replace(/\/$/, ""); setApi(base); load(base); }).catch(() => load()); }, [load]);

  useEffect(() => {
    if (!api || api === fallbackApi && typeof window !== "undefined" && window.location.hostname !== "localhost") return;
    const timer = setInterval(() => load(api), 15000);
    return () => clearInterval(timer);
  }, [api, load]);

  useEffect(() => {
    if (!api) return;
    const socket = new WebSocket(api.replace(/^http/, "ws") + "/ws/events");
    socket.onmessage = () => load(api);
    return () => socket.close();
  }, [api, load]);

  const visibleTasks = useMemo(() => filter === "all" ? tasks : tasks.filter((task) => (task.source || "manual") === filter), [filter, tasks]);

  async function saveTask(event: FormEvent) {
    event.preventDefault(); if (!title.trim()) return;
    try { await request<Task>(api, editing ? `/api/tasks/${editing}` : "/api/tasks", { method: editing ? "PATCH" : "POST", body: JSON.stringify({ titulo: title.trim(), estado: status }) }); setTitle(""); setStatus("Pendiente"); setEditing(null); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo guardar la tarea"); }
  }
  async function removeTask(id: string) { if (!confirm("¿Eliminar esta tarea?")) return; try { await request(api, `/api/tasks/${id}`, { method: "DELETE" }); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo eliminar"); } }
  function editTask(task: Task) { setEditing(task.id); setTitle(task.titulo); setStatus(task.estado); window.scrollTo({ top: 0, behavior: "smooth" }); }

  return <main className="shell">
    <header className="topbar"><div><p className="eyebrow">ARGUS / SISTEMA DISTRIBUIDO</p><h1>Centro de operaciones</h1><p className="muted">Tareas y vigilancia conectadas a la Máquina A.</p></div><div className={`health ${health}`}><span />{health === "healthy" ? "Backend conectado" : health === "checking" ? "Comprobando…" : "Backend offline"}</div></header>
    {error && <div className="alert">{error}<button onClick={() => load()}>Reintentar</button></div>}
    <section className="stats"><div><span>Tareas visibles</span><strong>{visibleTasks.length}</strong></div><div><span>Cámaras</span><strong>{cameras.length}</strong></div><div><span>Eventos recientes</span><strong>{events.length}</strong></div><div><span>Estado</span><strong className="accent">{String(summary?.status || (health === "healthy" ? "healthy" : "—"))}</strong></div></section>
    <section className="grid-layout">
      <div className="panel task-panel"><div className="panel-head"><div><p className="eyebrow">OPERACIONES</p><h2>{editing ? "Editar tarea" : "Nueva tarea"}</h2></div>{editing && <button className="ghost" onClick={() => { setEditing(null); setTitle(""); }}>Cancelar</button>}</div>
        <form onSubmit={saveTask} className="task-form"><input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="¿Qué necesita atención?" aria-label="Título de tarea" /><select value={status} onChange={(e) => setStatus(e.target.value)}><option>Pendiente</option><option>En progreso</option><option>Completada</option></select><button className="primary">{editing ? "Guardar cambios" : "Agregar tarea"}</button></form>
        <div className="filters"><button className={filter === "all" ? "selected" : ""} onClick={() => setFilter("all")}>Todas</button><button className={filter === "manual" ? "selected" : ""} onClick={() => setFilter("manual")}>Manuales</button><button className={filter === "camera" ? "selected" : ""} onClick={() => setFilter("camera")}>Vigilancia</button></div>
        {loading ? <div className="empty">Cargando información…</div> : visibleTasks.length === 0 ? <div className="empty">No hay tareas para mostrar.</div> : <div className="task-list">{visibleTasks.map((task) => <article className="task" key={task.id}><div className="task-check">{task.estado === "Completada" ? "✓" : ""}</div><div className="task-body"><div className="task-title"><h3>{task.titulo}</h3><span className={`tag ${task.source === "camera" ? "camera-tag" : ""}`}>{task.source === "camera" ? "VIGILANCIA" : "MANUAL"}</span></div><p>{task.camera_id ? `Cámara ${task.camera_id} · Prioridad ${task.priority || "media"}` : task.estado}</p></div><div className="actions"><button onClick={() => editTask(task)} aria-label="Editar tarea">Editar</button><button onClick={() => removeTask(task.id)} aria-label="Eliminar tarea">Eliminar</button></div></article>)}</div>}
      </div>
      <aside className="side-column"><div className="panel"><div className="panel-head"><div><p className="eyebrow">NODOS EDGE</p><h2>Cámaras</h2></div><span className="live-dot">● LIVE</span></div>{cameras.length === 0 ? <div className="empty small">No hay cámaras registradas.</div> : <div className="camera-grid">{cameras.map((camera) => <div className="camera" key={camera.camera_id || camera.id}><div className="camera-view">{camera.stream_url ? <img src={camera.stream_url} alt={camera.name || "Stream de cámara"} /> : <span>SEÑAL NO DISPONIBLE</span>}</div><div className="camera-info"><strong>{camera.name || camera.camera_id || camera.id}</strong><span>{camera.location || "Ubicación no definida"}</span><small className={camera.status === "online" || camera.state === "online" ? "online" : "offline"}>● {camera.status || camera.state || "unknown"} {camera.fps ? `· ${camera.fps} FPS` : ""}</small></div></div>)}</div>}</div>
        <div className="panel events"><div className="panel-head"><div><p className="eyebrow">MONITOREO</p><h2>Últimos eventos</h2></div></div>{events.length === 0 ? <div className="empty small">Esperando eventos del Edge…</div> : <div className="event-list">{events.slice(0, 5).map((item, index) => <div className="event" key={item.id || item.event_id || index}><span className="event-line" /><div><strong>{item.type || item.object_name || "Evento"}</strong><p>{item.description || `Cámara ${item.camera_id || "—"}`}</p></div><small>{item.confidence ? `${Math.round(item.confidence * 100)}%` : "ahora"}</small></div>)}</div>}</div>
      </aside>
    </section>
    <footer>API: <code>{api}</code><span>Polling de respaldo · WebSocket de eventos</span></footer>
  </main>;
}
