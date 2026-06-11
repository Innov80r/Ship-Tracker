import React, { useEffect, useMemo, useState } from 'react'
import useAlerts from '../hooks/useAlerts'
import useAlertStore from '../store/alertStore'
import useIntelStore from '../store/intelStore'
import { PageHeader, Panel, Pill, StatTile } from '../components/ui/CommandPrimitives'
import { formatTimeAgo, formatTimestamp } from '../utils/formatters'
import { getApi, postApi } from '../utils/api'

export default function AlertsPage() {
  const { markAsRead, markAllAsRead } = useAlerts(false)
  const alerts = useAlertStore((state) => state.alerts)
  const unreadCount = useAlertStore((state) => state.unreadCount)
  const notificationRules = useIntelStore((state) => state.notificationRules)
  const toggleNotificationRule = useIntelStore((state) => state.toggleNotificationRule)
  const browserNotificationsEnabled = useIntelStore((state) => state.browserNotificationsEnabled)
  const setBrowserNotificationsEnabled = useIntelStore((state) => state.setBrowserNotificationsEnabled)
  const webhookEndpoints = useIntelStore((state) => state.webhookEndpoints)
  const addWebhookEndpoint = useIntelStore((state) => state.addWebhookEndpoint)
  const toggleWebhookEndpoint = useIntelStore((state) => state.toggleWebhookEndpoint)
  const removeWebhookEndpoint = useIntelStore((state) => state.removeWebhookEndpoint)
  const [permissionState, setPermissionState] = useState(
    typeof Notification === 'undefined' ? 'unsupported' : Notification.permission,
  )
  const [deliveries, setDeliveries] = useState([])
  const [deliveryLoading, setDeliveryLoading] = useState(false)
  const [testChannel, setTestChannel] = useState('webhook')
  const [testTarget, setTestTarget] = useState('')
  const [testTitle, setTestTitle] = useState('Sea Tracker test')
  const [testMessage, setTestMessage] = useState('Command-center notification path validation.')
  const [testSending, setTestSending] = useState(false)
  const [testResult, setTestResult] = useState(null)

  useEffect(() => {
    let cancelled = false

    const loadDeliveries = async () => {
      setDeliveryLoading(true)
      try {
        const data = await getApi('/api/notifications/deliveries', { params: { limit: 24 } })
        if (!cancelled) {
          setDeliveries(data.deliveries || [])
        }
      } catch {
        if (!cancelled) {
          setDeliveries([])
        }
      } finally {
        if (!cancelled) {
          setDeliveryLoading(false)
        }
      }
    }

    loadDeliveries()
    const intervalId = window.setInterval(loadDeliveries, 15000)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  const deliveryStats = useMemo(() => ({
    failed: deliveries.filter((delivery) => delivery.status === 'failed').length,
    retrying: deliveries.filter((delivery) => delivery.status === 'retrying').length,
    delivered: deliveries.filter((delivery) => delivery.status === 'delivered').length,
    activeEndpoints: webhookEndpoints.filter((endpoint) => endpoint.enabled).length,
  }), [deliveries, webhookEndpoints])

  const requestBrowserNotifications = async () => {
    if (typeof Notification === 'undefined') return
    const permission = await Notification.requestPermission()
    setPermissionState(permission)
    setBrowserNotificationsEnabled(permission === 'granted')
  }

  const loadDeliveriesNow = async () => {
    try {
      const data = await getApi('/api/notifications/deliveries', { params: { limit: 24 } })
      setDeliveries(data.deliveries || [])
    } catch {
      setDeliveries([])
    }
  }

  const handleAddWebhook = () => {
    const name = window.prompt('Endpoint label')
    if (!name) return
    const url = window.prompt('Target URL or recipient (webhook URL, mailto:, token:chat_id, etc.)')
    if (!url) return
    const channel = window.prompt('Channel label (slack, discord, email, telegram, webhook)', 'webhook') || 'webhook'
    addWebhookEndpoint({ name, url, channel })
  }

  const handleRetryFailed = async () => {
    try {
      await postApi('/api/notifications/retry-failed?limit=25')
      await loadDeliveriesNow()
    } catch {}
  }

  const handleRetryDelivery = async (deliveryId) => {
    try {
      await postApi(`/api/notifications/deliveries/${deliveryId}/retry`)
      await loadDeliveriesNow()
    } catch {}
  }

  const handleSendTest = async () => {
    if (!testTarget.trim()) return
    setTestSending(true)
    setTestResult(null)
    try {
      const response = await postApi('/api/notifications/test', {
        channel: testChannel,
        target: testTarget.trim(),
        title: testTitle.trim() || 'Sea Tracker test',
        message: testMessage.trim() || 'Command-center notification path validation.',
        event_type: 'test',
        severity: 'info',
      })
      const delivery = response?.delivery
      if (response?.error) {
        setTestResult({ tone: 'rose', message: response.error })
      } else if (delivery?.status === 'delivered') {
        setTestResult({ tone: 'emerald', message: 'Test notification delivered.' })
      } else if (delivery?.last_error) {
        setTestResult({ tone: 'rose', message: delivery.last_error })
      } else if (delivery?.status) {
        setTestResult({ tone: delivery.status === 'retrying' ? 'amber' : 'slate', message: `Delivery status: ${delivery.status}` })
      } else {
        setTestResult({ tone: 'slate', message: 'Test request completed with no delivery details returned.' })
      }
      await loadDeliveriesNow()
    } catch (error) {
      setTestResult({ tone: 'rose', message: error?.message || 'Test notification request failed.' })
    } finally {
      setTestSending(false)
    }
  }

  return (
    <div className="page-scroll" id="alerts-page">
      <PageHeader
        eyebrow="Notifications"
        title="Alert Automation Center"
        subtitle="Manage live alerts, browser notifications, outbound endpoints, retry queues, and backend delivery logs for webhook, Slack, Discord, Telegram, and email channels."
        actions={(
          <>
            <button type="button" className="btn-ghost" onClick={markAllAsRead}>Mark all read</button>
            <button type="button" className="btn-ghost" onClick={handleRetryFailed}>Retry failed</button>
            <button type="button" className="btn-primary" onClick={requestBrowserNotifications}>
              {browserNotificationsEnabled ? 'Browser enabled' : 'Enable browser alerts'}
            </button>
          </>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Unread" value={unreadCount} caption="Unacknowledged alerts in the feed" tone="amber" />
        <StatTile label="Loaded alerts" value={alerts.length} caption="Current alert feed entries" tone="cyan" />
        <StatTile label="Active endpoints" value={deliveryStats.activeEndpoints} caption="Enabled outbound notification targets" tone="emerald" />
        <StatTile label="Failed deliveries" value={deliveryStats.failed + deliveryStats.retrying} caption="Failures and pending retries in the delivery log" tone="rose" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel title="Browser notifications" subtitle="Local desktop notifications driven by the live websocket feed">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Pill tone={browserNotificationsEnabled ? 'emerald' : 'amber'}>{browserNotificationsEnabled ? 'Enabled' : 'Disabled'}</Pill>
              <Pill tone="slate">{permissionState}</Pill>
            </div>
            <div className="text-sm leading-6 text-slate-400">
              Browser notifications remain the fastest local alert path. External channels below are now backed by server-side delivery logs and retry handling.
            </div>
          </div>
        </Panel>

        <Panel title="Outbound test console" subtitle="Validate a webhook, chat channel, or email target against the backend notifier">
          <div className="grid gap-3 md:grid-cols-2">
            <label className="block">
              <div className="eyebrow-sm">Channel</div>
              <select value={testChannel} onChange={(event) => setTestChannel(event.target.value)} className="input-field mt-2 w-full">
                <option value="webhook">Webhook</option>
                <option value="slack">Slack</option>
                <option value="discord">Discord</option>
                <option value="telegram">Telegram</option>
                <option value="email">Email</option>
              </select>
            </label>

            <label className="block">
              <div className="eyebrow-sm">Target</div>
              <input
                type="text"
                value={testTarget}
                onChange={(event) => setTestTarget(event.target.value)}
                className="input-field mt-2 w-full"
                placeholder="Webhook URL, mailto:ops@..., or token:chat_id"
              />
            </label>

            <label className="block">
              <div className="eyebrow-sm">Title</div>
              <input type="text" value={testTitle} onChange={(event) => setTestTitle(event.target.value)} className="input-field mt-2 w-full" />
            </label>

            <label className="block">
              <div className="eyebrow-sm">Registry quick-fill</div>
              <select
                value=""
                onChange={(event) => {
                  const endpoint = webhookEndpoints.find((entry) => String(entry.id) === event.target.value)
                  if (!endpoint) return
                  setTestChannel(endpoint.channel || 'webhook')
                  setTestTarget(endpoint.url || '')
                }}
                className="input-field mt-2 w-full"
              >
                <option value="">Choose a saved endpoint</option>
                {webhookEndpoints.map((endpoint) => (
                  <option key={endpoint.id} value={endpoint.id}>{endpoint.name}</option>
                ))}
              </select>
            </label>
          </div>

          <label className="mt-3 block">
            <div className="eyebrow-sm">Message</div>
            <textarea value={testMessage} onChange={(event) => setTestMessage(event.target.value)} className="input-field mt-2 min-h-24 w-full" />
          </label>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button type="button" className="btn-primary" onClick={handleSendTest} disabled={testSending || !testTarget.trim()}>
              {testSending ? 'Sending…' : 'Send test'}
            </button>
            <Pill tone="slate">{deliveryLoading ? 'Refreshing log…' : `${deliveryStats.delivered} delivered`}</Pill>
          </div>
          {testResult && (
            <div className={`mt-3 text-sm ${testResult.tone === 'emerald' ? 'text-emerald-400' : testResult.tone === 'amber' ? 'text-amber-400' : testResult.tone === 'rose' ? 'text-rose-400' : 'text-slate-400'}`}>
              {testResult.message}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Panel title="Webhook registry" subtitle="Saved outbound endpoints synced through the workspace snapshot" action={(
          <button type="button" className="btn-primary" onClick={handleAddWebhook}>Add endpoint</button>
        )}>
          {webhookEndpoints.length === 0 ? (
            <div className="text-sm text-slate-500">No outbound endpoints configured yet.</div>
          ) : (
            <div className="space-y-2">
              {webhookEndpoints.map((endpoint) => (
                <div key={endpoint.id} className="intel-row">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{endpoint.name}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">{endpoint.channel} · {endpoint.url}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button type="button" className="btn-ghost" onClick={() => toggleWebhookEndpoint(endpoint.id)}>
                      {endpoint.enabled ? 'Enabled' : 'Disabled'}
                    </button>
                    <button type="button" className="btn-ghost" onClick={() => removeWebhookEndpoint(endpoint.id)}>
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Automation rules" subtitle="Severity and event-level routing controls from workspace state">
          <div className="space-y-2">
            {notificationRules.map((rule) => (
              <div key={rule.id} className="intel-row">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{rule.name}</div>
                  <div className="mt-1 truncate text-xs text-slate-500">{rule.channel} · {rule.event} · {rule.severity}</div>
                </div>
                <button type="button" className="btn-ghost" onClick={() => toggleNotificationRule(rule.id)}>
                  {rule.enabled ? 'Enabled' : 'Disabled'}
                </button>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Delivery log" subtitle="Recent backend delivery outcomes with retry visibility">
          {deliveries.length === 0 ? (
            <div className="text-sm text-slate-500">No notification deliveries logged yet.</div>
          ) : (
            <div className="space-y-2">
              {deliveries.map((delivery) => (
                <div key={delivery.id} className="intel-row">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{delivery.event_type} · {delivery.channel}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">
                      {delivery.target || 'No target'} · {formatTimestamp(delivery.created_at)}
                    </div>
                    <div className="mt-2 text-[11px] text-slate-600">
                      Attempt {delivery.attempt_count}
                      {delivery.response_status ? ` · HTTP ${delivery.response_status}` : ''}
                      {delivery.last_error ? ` · ${delivery.last_error}` : ''}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Pill tone={deliveryTone(delivery.status)}>{delivery.status}</Pill>
                    {delivery.status !== 'delivered' && (
                      <button type="button" className="btn-ghost" onClick={() => handleRetryDelivery(delivery.id)}>
                        Retry
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Live alert feed" subtitle="Newest alerts from the live websocket and API feed">
          {alerts.length === 0 ? (
            <div className="text-sm text-slate-500">No alerts in the feed right now.</div>
          ) : (
            <div className="space-y-2">
              {alerts.map((alert) => (
                <button
                  key={alert.id}
                  type="button"
                  onClick={() => !alert.is_read && markAsRead(alert.id)}
                  className={`intel-row cursor-pointer text-left transition hover:border-cyan-400/20 hover:bg-cyan-400/5 ${alert.is_read ? 'opacity-70' : ''}`}
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-white">{alert.title}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">{alert.message}</div>
                    <div className="mt-2 text-[11px] text-slate-600">{formatTimeAgo(alert.created_at)} · {alert.alert_type} · {alert.vessel_name || 'Unknown vessel'}</div>
                  </div>
                  <Pill tone={alert.severity === 'critical' ? 'rose' : alert.severity === 'warning' ? 'amber' : 'cyan'}>
                    {alert.severity || 'info'}
                  </Pill>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}

function deliveryTone(status) {
  if (status === 'delivered') return 'emerald'
  if (status === 'failed') return 'rose'
  if (status === 'retrying' || status === 'sending') return 'amber'
  return 'slate'
}
