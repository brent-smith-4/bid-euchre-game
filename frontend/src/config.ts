// "127.0.0.1" rather than "localhost" - uvicorn only binds the IPv4
// loopback, and resolving "localhost" makes the browser waste time on a
// doomed IPv6 (::1) attempt first before falling back.
export const WS_BASE: string = import.meta.env.VITE_WS_BASE ?? "ws://127.0.0.1:8000";
export const HTTP_BASE: string = import.meta.env.VITE_HTTP_BASE ?? "http://127.0.0.1:8000";
