import { defineStore } from 'pinia';
import { Notify } from 'quasar';
import { api, apiUrl } from 'src/axios-instance';
import { useBmsStore } from 'src/stores/bms';
import { useDeyeStore } from 'src/stores/deye';
import { usePowerStore } from 'src/stores/power';
import { useTapoStore } from 'src/stores/tapo';
import { readonly, ref } from 'vue';

const RECONNECT_DELAY_MS = 5000;

/**
 * One Server-Sent Events connection instead of polling 4 endpoints every 2 s.
 * The server pushes a topic only when it changed. While `connected` is false the pages keep polling.
 */
export const useLiveStore = defineStore('live', () => {
  const connected = ref(false);
  let source: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let users = 0;

  const handlers: Record<string, (data: any) => void> = {
    cell_info: (data) => useBmsStore().updateCellInfo(data || {}),
    deye: (data) => useDeyeStore().updateDeyeData(Array.isArray(data) ? data : []),
    tapo_top: (data) => useTapoStore().updateTopDevices(Array.isArray(data) ? data : []),
    power: (data) => {
      const now = Date.now() / 1000;
      // duration_s is not streamed (it would change every second): derive it locally.
      (data?.devices || []).forEach((d: any) => (d.duration_s = Math.max(0, now - (d.off_since || now))));
      usePowerStore().updatePowerData(data);
    },
    alert: (data) =>
      Notify.create({
        message: `🚨 ${data?.device_name}: ${data?.message}`,
        color: data?.level === 'critical' ? 'red' : 'orange',
        position: 'top',
        timeout: 8000,
      }),
  };

  async function buildUrl(): Promise<string> {
    let url = `${apiUrl}/api/stream`;
    // When public read access is disabled, EventSource (no custom headers) needs a one-time ticket.
    if (localStorage.getItem('access_token')) {
      try {
        const { data } = await api.post('/api/stream/ticket', {}, { timeout: 6000 });
        if (data?.ticket) url += `?ticket=${encodeURIComponent(data.ticket)}`;
      } catch {
        /* public read is enough without a ticket */
      }
    }
    return url;
  }

  function close() {
    source?.close();
    source = null;
    connected.value = false;
  }

  function scheduleReconnect() {
    if (reconnectTimer || users === 0) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      void open();
    }, RECONNECT_DELAY_MS);
  }

  async function open() {
    if (source || users === 0 || typeof EventSource === 'undefined') return;
    const url = await buildUrl();
    if (users === 0) return;
    const es = new EventSource(url);
    source = es;
    es.onopen = () => (connected.value = true);
    es.onerror = () => {
      // Tickets are single-use, so let the browser's auto-reconnect go and reconnect ourselves.
      close();
      scheduleReconnect();
    };
    Object.entries(handlers).forEach(([event, handler]) =>
      es.addEventListener(event, (e) => {
        try {
          handler(JSON.parse((e as MessageEvent).data));
        } catch (err) {
          console.warn(`Live event "${event}" could not be handled`, err);
        }
      })
    );
  }

  /** Reference counted: the connection stays open while at least one page uses it. */
  function start() {
    users += 1;
    void open();
  }

  function stop() {
    users = Math.max(0, users - 1);
    if (users === 0) {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = null;
      close();
    }
  }

  return {
    get connected() {
      return readonly(connected);
    },
    isConnected: () => connected.value,
    start,
    stop,
  };
});
