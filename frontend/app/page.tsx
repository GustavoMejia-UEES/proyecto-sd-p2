"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Task = { id: string; titulo: string; estado: string; source?: string; camera_id?: string; event_id?: string; event_type?: string; priority?: string; occurrences?: number; last_event_id?: string; last_seen_at?: string };
type Camera = { camera_id?: string; id?: string; name?: string; type?: string; location?: string; status?: string; state?: string; fps?: number; stream_url?: string; source?: string; vision_mode?: string; detections?: number; last_heartbeat?: string; enabled?: boolean };
type EventItem = { id?: string; event_id?: string; camera_id?: string; type?: string; object_name?: string; description?: string; confidence?: number; status?: string; timestamp?: string; created_at?: string };
type Health = "checking" | "healthy" | "offline";

const fallbackApi = "http://localhost:8000";
const cameraInventory = [
  { id: "CAM-001", name: "Cámara laptop Gustavo", type: "integrated" },
  { id: "CAM-002", name: "Cámara USB Gustavo", type: "usb" },
  { id: "CAM-003", name: "Teléfono Gustavo", type: "phone" },
  { id: "CAM-004", name: "Cámara laptop Juanfer", type: "integrated" },
  { id: "CAM-005", name: "Teléfono Juanfer", type: "phone" },
];

async function request<T>(api: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${api}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!response.ok) throw new Error((await response.text()) || `Error ${response.status}`);
  return response.status === 204 ? (undefined as T) : response.json();
}

function arrayFrom<T>(value: unknown): T[] { return Array.isArray(value) ? value : ((value as { items?: T[] })?.items || []); }
function cameraId(camera: Camera) { return camera.camera_id || camera.id || "unknown"; }
function eventId(event: EventItem) { return event.event_id || event.id || ""; }
function normalizeCameras(items: Camera[]) { return cameraInventory.map((expected) => { const found = items.find((item) => cameraId(item) === expected.id); return found ? { ...expected, ...found } : { ...expected, id: expected.id, status: "unknown" }; }); }
function cameraStatus(camera: Camera) { return camera.status || camera.state || "unknown"; }
function cameraIsOnline(camera: Camera) { return cameraStatus(camera) === "online" && (camera.fps === undefined || camera.fps > 0); }

export default function Home() {
  const [api, setApi] = useState(fallbackApi);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [title, setTitle] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [status, setStatus] = useState("Pendiente");
  const [priority, setPriority] = useState("high");
  const [selectedCamera, setSelectedCamera] = useState("");
  const [selectedEvent, setSelectedEvent] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [eventCameraFilter, setEventCameraFilter] = useState("all");
  const [cameraPage, setCameraPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [health, setHealth] = useState<Health>("checking");

  const load = useCallback(async (base = api) => {
    setLoading(true); setError("");
    try {
      const [taskData, cameraData, eventData] = await Promise.all([
        request<unknown>(base, "/api/tasks"),
        request<unknown>(base, "/api/cameras"),
        request<unknown>(base, "/api/events?limit=50"),
      ]);
      setTasks(arrayFrom<Task>(taskData));
      setCameras(normalizeCameras(arrayFrom<Camera>(cameraData)));
      setEvents(arrayFrom<EventItem>(eventData));
      await request(base, "/health");
      setHealth("healthy");
    } catch (e) {
      setHealth("offline");
      setError(e instanceof Error ? e.message : "Se perdió la conexión con el backend");
    } finally { setLoading(false); }
  }, [api]);

  useEffect(() => {
    fetch("/api/config").then((r) => r.json()).then((v: { apiUrl?: string }) => {
      const base = (v.apiUrl || fallbackApi).replace(/\/$/, ""); setApi(base); load(base);
    }).catch(() => load());
  }, [load]);

  useEffect(() => {
    const timer = setInterval(() => load(api), 10000);
    return () => clearInterval(timer);
  }, [api, load]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;
    let attempt = 0;
    const connect = () => {
      if (stopped) return;
      socket = new WebSocket(api.replace(/^http/, "ws") + "/ws/events");
      socket.onopen = () => { attempt = 0; setError(""); };
      socket.onmessage = (message) => {
        try { const payload = JSON.parse(message.data) as { type?: string; event?: EventItem }; if (["camera_status", "event_created", "event_updated", "event_deleted", "task_created", "task_updated"].includes(payload.type || "")) load(api); } catch { load(api); }
      };
      socket.onclose = () => { if (!stopped) { setError("WebSocket desconectado; reconectando y usando polling."); reconnectTimer = setTimeout(connect, Math.min(30000, 1000 * 2 ** attempt)); attempt += 1; } };
      socket.onerror = () => socket?.close();
    };
    connect();
    return () => { stopped = true; if (reconnectTimer) clearTimeout(reconnectTimer); socket?.close(); };
  }, [api, load]);

  const filteredEvents = useMemo(() => eventCameraFilter === "all" ? events : events.filter((item) => item.camera_id === eventCameraFilter), [eventCameraFilter, events]);
  const selectedCameraEvents = useMemo(() => events.filter((item) => item.camera_id === selectedCamera), [events, selectedCamera]);
  const cameraPages = Math.max(1, Math.ceil(cameras.length / 4));
  const visibleCameras = cameras.slice(cameraPage * 4, cameraPage * 4 + 4);

  useEffect(() => { if (cameraPage >= cameraPages) setCameraPage(cameraPages - 1); }, [cameraPage, cameraPages]);

  async function saveTask(event: FormEvent) {
    event.preventDefault(); if (!title.trim()) return;
    const payload: Record<string, string> = { titulo: title.trim(), estado: status };
    if (selectedCamera) { payload.source = "camera"; payload.camera_id = selectedCamera; if (selectedEvent) payload.event_id = selectedEvent; payload.priority = priority; }
    try {
      await request<Task>(api, editing ? `/api/tasks/${editing}` : "/api/tasks", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
      resetForm(); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo guardar la tarea"); }
  }

  function resetForm() { setTitle(""); setStatus("Pendiente"); setPriority("high"); setSelectedCamera(""); setSelectedEvent(""); setEditing(null); setModalOpen(false); }
  function openNewTask(camera = "", event = "") { resetForm(); setSelectedCamera(camera); setSelectedEvent(event); setModalOpen(true); }
  async function removeTask(id: string) { if (!confirm("¿Eliminar esta tarea?")) return; try { await request(api, `/api/tasks/${id}`, { method: "DELETE" }); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo eliminar"); } }
  async function toggleCamera(camera: Camera) { const id = cameraId(camera); try { await request(api, `/api/cameras/${id}/control`, { method: "POST", body: JSON.stringify({ enabled: camera.enabled === false }) }); await load(); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo cambiar el estado de la cámara"); } }
  function editTask(task: Task) { setEditing(task.id); setTitle(task.titulo); setStatus(task.estado); setSelectedCamera(task.camera_id || ""); setSelectedEvent(task.event_id || ""); setPriority(task.priority || "high"); setModalOpen(true); }

  return <main className="shell">
    <header className="topbar"><div><p className="eyebrow">ARGUS / RED DE VIGILANCIA</p><h1>Centro de cámaras</h1><p className="muted">Nodos Edge, eventos y tareas operativas en tiempo real.</p></div><div className={`health ${health}`}><span />{health === "healthy" ? "Backend conectado" : health === "checking" ? "Comprobando…" : "Conexión perdida"}</div></header>
    {error && <div className="alert">{error}<button onClick={() => load()}>Reintentar conexión</button></div>}

    <section className="camera-section"><div className="section-heading"><div><p className="eyebrow">NODOS EDGE · 5 ESPACIOS RESERVADOS</p><h2>Cámaras conectadas</h2></div><div className="camera-navigation"><span className="live-dot">● STREAMS EN VIVO</span>{cameraPages > 1 && <><button className="nav-button" onClick={() => setCameraPage((page) => Math.max(0, page - 1))} disabled={cameraPage === 0}>‹ Anterior</button><span className="page-indicator">{cameraPage + 1} / {cameraPages}</span><button className="nav-button" onClick={() => setCameraPage((page) => Math.min(cameraPages - 1, page + 1))} disabled={cameraPage === cameraPages - 1}>Siguiente ›</button></>}</div></div>
      {loading ? <div className="empty camera-empty">Conectando con los nodos…</div> : cameras.length === 0 ? <div className="lost-connection"><strong>Sin cámaras conectadas</strong><span>No se detectan nodos Edge o se perdió la conexión con el backend.</span><button className="primary small-button" onClick={() => load()}>Buscar cámaras</button></div> : <div className="camera-grid">{visibleCameras.map((camera) => { const online = cameraIsOnline(camera) && health !== "offline"; return <article className={`camera ${online ? "camera-online" : "camera-offline"}`} key={cameraId(camera)}><div className="camera-view">{online && camera.stream_url ? <img src={camera.stream_url} alt={`Stream de ${camera.name || cameraId(camera)}`} /> : <div className="lost-feed"><span>!</span><strong>{health === "offline" ? "CONEXIÓN PERDIDA" : "CÁMARA OFFLINE"}</strong><small>{cameraStatus(camera) === "unknown" ? "Esperando registro del nodo" : "No hay señal disponible"}</small></div>}<span className={`camera-status ${online ? "online" : "offline"}`}>● {online ? "ONLINE" : cameraStatus(camera).toUpperCase()}</span></div><div className="camera-info"><div><strong>{camera.name || cameraId(camera)}</strong><span>{camera.location || "Nodo Edge"}</span></div><small className={online ? "online-text" : "offline-text"}>● {online ? `${camera.fps || 0} FPS` : "Sin conexión"} {camera.vision_mode ? `· ${camera.vision_mode}` : ""}</small><button className="camera-task-button" onClick={() => openNewTask(cameraId(camera))}>✎ Crear tarea para esta cámara</button></div></article>; })}</div>}
    </section>

    <section className="operations-grid"><div className="panel events"><div className="panel-head"><div><p className="eyebrow">LOG DISTRIBUIDO</p><h2>Eventos de las cámaras</h2></div><select value={eventCameraFilter} onChange={(e) => setEventCameraFilter(e.target.value)}><option value="all">Todas las cámaras</option>{cameras.map((camera) => <option key={cameraId(camera)} value={cameraId(camera)}>{camera.name || cameraId(camera)}</option>)}</select></div>{filteredEvents.length === 0 ? <div className="empty small">Esperando eventos de los nodos Edge…</div> : <div className="event-list">{filteredEvents.slice(0, 20).map((item, index) => <div className="event" key={eventId(item) || index}><span className="event-line" /><div><strong>{item.type || item.object_name || "Evento"}</strong><p>{item.description || "Detección reportada por la cámara"}</p><small>Cámara: {item.camera_id || "—"}</small></div><span className="event-confidence">{item.confidence ? `${Math.round(item.confidence * 100)}%` : "nuevo"}</span><button className="assign-event" onClick={() => openNewTask(item.camera_id || "", eventId(item))}>Asignar tarea</button></div>)}</div>}</div>
      <div className="panel task-panel" id="task-form"><div className="panel-head"><div><p className="eyebrow">RECURSOS OPERATIVOS</p><h2>{editing ? "Editar tarea" : "Crear tarea"}</h2></div><div className="task-heading-actions">{editing && <button className="ghost" onClick={resetForm}>Cancelar</button>}<button className="icon-button add-task-button" onClick={() => openNewTask()} aria-label="Agregar tarea" title="Agregar tarea">✎</button></div></div><form onSubmit={saveTask} className="task-form"><input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ej. Revisar cámara 1" aria-label="Título de tarea" /><select value={selectedCamera} onChange={(e) => { setSelectedCamera(e.target.value); setSelectedEvent(""); }}><option value="">Tarea manual</option>{cameras.map((camera) => <option key={cameraId(camera)} value={cameraId(camera)}>Vigilancia: {camera.name || cameraId(camera)}</option>)}</select>{selectedCamera && <select value={selectedEvent} onChange={(e) => setSelectedEvent(e.target.value)}><option value="">Sin evento específico</option>{selectedCameraEvents.map((item, index) => <option key={eventId(item) || index} value={eventId(item)}>{item.type || item.object_name || "Evento"} — {item.description || "detección"}</option>)}</select>}<select value={status} onChange={(e) => setStatus(e.target.value)}><option>Pendiente</option><option>En progreso</option><option>Completada</option></select>{selectedCamera && <select value={priority} onChange={(e) => setPriority(e.target.value)}><option value="high">Alta</option><option value="medium">Media</option><option value="low">Baja</option></select>}<button className="primary">{editing ? "Guardar cambios" : "Agregar tarea"}</button></form><div className="task-list compact">{tasks.length === 0 ? <div className="empty small">Las tareas aparecerán aquí.</div> : tasks.map((task) => <article className="task" key={task.id}><div className="task-body"><div className="task-title"><h3>{task.titulo}</h3><span className={`tag ${task.source === "camera" ? "camera-tag" : ""}`}>{task.source === "camera" ? `CAM ${task.camera_id || "—"}` : "MANUAL"}</span></div><p>{task.estado}{task.source === "camera" ? ` · Prioridad ${task.priority || "media"}` : ""}{task.event_id ? ` · Evento ${task.event_id}` : ""}</p></div><div className="actions"><button onClick={() => editTask(task)}>Editar</button><button onClick={() => removeTask(task.id)}>Eliminar</button></div></article>)}</div></div></section>
    {modalOpen && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) resetForm(); }}><div className="task-modal" role="dialog" aria-modal="true" aria-labelledby="task-modal-title"><div className="modal-head"><div><p className="eyebrow">RECURSO OPERATIVO</p><h2 id="task-modal-title">{editing ? "Editar tarea" : "Nueva tarea"}</h2></div><button className="modal-close" onClick={resetForm} aria-label="Cerrar">×</button></div><form onSubmit={saveTask} className="modal-form"><label>Título<input autoFocus value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ej. Revisar cámara 1" /></label><label>Origen<select value={selectedCamera} onChange={(e) => { setSelectedCamera(e.target.value); setSelectedEvent(""); }}><option value="">Tarea manual</option>{cameras.map((camera) => <option key={cameraId(camera)} value={cameraId(camera)}>Vigilancia: {camera.name || cameraId(camera)}</option>)}</select></label>{selectedCamera && <label>Evento relacionado<select value={selectedEvent} onChange={(e) => setSelectedEvent(e.target.value)}><option value="">Sin evento específico</option>{selectedCameraEvents.map((item, index) => <option key={eventId(item) || index} value={eventId(item)}>{item.type || item.object_name || "Evento"} — {item.description || "detección"}</option>)}</select></label>}<label>Estado<select value={status} onChange={(e) => setStatus(e.target.value)}><option>Pendiente</option><option>En progreso</option><option>Completada</option></select></label>{selectedCamera && <label>Prioridad<select value={priority} onChange={(e) => setPriority(e.target.value)}><option value="high">Alta</option><option value="medium">Media</option><option value="low">Baja</option></select></label>}<div className="modal-actions"><button type="button" className="ghost" onClick={resetForm}>Cancelar</button><button className="primary">{editing ? "Guardar cambios" : "Crear tarea"}</button></div></form></div></div>}
    <footer>API: <code>{api}</code><span>WebSocket de eventos · Polling de respaldo cada 15s</span></footer>
  </main>;
}
