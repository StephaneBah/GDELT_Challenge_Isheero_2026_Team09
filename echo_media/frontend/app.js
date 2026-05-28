import { createApp, ref, computed, nextTick } from 'https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'

const API = ''

// ── Markdown minimal ──────────────────────────────────────────────────────────
function md(text) {
  if (!text) return ''
  return text
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*?<\/li>\n?)+/gs, m => `<ul>${m}</ul>`)
    .replace(/\n\n+/g, '</p><p>')
    .replace(/^(?!<[huolp])(.+)$/gm, m => m.trim() ? `<p>${m}</p>` : '')
    .replace(/<p><\/p>/g, '')
}

// ── SSE helper ────────────────────────────────────────────────────────────────
async function sse(url, body, onChunk, onDone) {
  try {
    const res = await fetch(API + url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) { onDone(); return }
    const reader = res.body.getReader()
    const dec = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      const lines = buf.split('\n'); buf = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const p = line.slice(6).trim()
        if (p === '[DONE]') { onDone(); return }
        try { const { text } = JSON.parse(p); onChunk(text) } catch {}
      }
    }
  } catch {}
  onDone()
}

// ── App ───────────────────────────────────────────────────────────────────────
createApp({
  setup() {
    const phase          = ref('landing')
    const selectedSector = ref('libre')
    const firstMessage   = ref('')
    const followupMessage= ref('')
    const isProcessing   = ref(false)
    const loadingBlock   = ref(false)
    const pendingQuestion= ref('')
    const streamEl       = ref(null)

    // Chaque élément = un échange complet (question + réponse système ou follow-up)
    const blocks = ref([])
    const currentSector = ref('libre')
    const currentSummary = ref(null)  // summary du dernier bloc principal

    const sectors = [
      {
        id: 'economie', label: 'Économie', desc: 'Échanges, sanctions, aide éco.',
        icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
      },
      {
        id: 'diplomatie', label: 'Diplomatie', desc: 'Visites, négociations, ruptures',
        icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`,
      },
      {
        id: 'cooperation', label: 'Coopération', desc: 'Aide fournie, accords, cessions',
        icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
      },
      {
        id: 'conflits', label: 'Conflits', desc: 'Menaces, combats, coercitions',
        icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      },
      {
        id: 'libre', label: 'Exploration', desc: 'Tous secteurs',
        icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
      },
    ]

    const currentSectorLabel = computed(
      () => sectors.find(s => s.id === currentSector.value)?.label || 'Exploration'
    )

    const canStart = computed(() => firstMessage.value.trim() || selectedSector.value !== 'libre')

    // Helpers couleur
    const toneClass  = (v) => !v ? 'neutral' : v > 0.5 ? 'pos' : v < -0.5 ? 'neg' : 'neu'
    const goldClass  = (v) => !v ? 'neutral' : v > 0.5 ? 'pos' : v < -0.5 ? 'neg' : 'neu'
    const tensionClass = (v) => !v ? 'neutral' : v > 65 ? 't-high' : v > 42 ? 't-mid' : 't-low'

    const shortUrl = (url) => {
      try { const u = new URL(url); return u.hostname + u.pathname.slice(0, 24) + (u.pathname.length > 24 ? '…' : '') }
      catch { return url.slice(0, 36) + '…' }
    }

    async function scrollDown() {
      await nextTick()
      if (streamEl.value) streamEl.value.scrollTop = streamEl.value.scrollHeight
    }

    function renderCharts(blockIdx, chartsData) {
      const cfg = { responsive: true, displayModeBar: false }

      // Attend que les divs soient dans le DOM avec des dimensions réelles
      function tryRender(attempt = 0) {
        const el = document.getElementById(`tension-${blockIdx}`)
        if (!el || el.offsetWidth === 0) {
          if (attempt < 20) setTimeout(() => tryRender(attempt + 1), 80)
          return
        }
        if (chartsData.tension) {
          const s = JSON.parse(chartsData.tension)
          Plotly.newPlot(`tension-${blockIdx}`, s.data, s.layout, cfg)
        }
        if (chartsData.bubble) {
          const s = JSON.parse(chartsData.bubble)
          Plotly.newPlot(`bubble-${blockIdx}`, s.data, s.layout, cfg)
        }
        if (chartsData.signal) {
          const s = JSON.parse(chartsData.signal)
          Plotly.newPlot(`signal-${blockIdx}`, s.data, s.layout, cfg)
        }
      }

      nextTick(() => tryRender())
    }

    // ── Pipeline principal ────────────────────────────────────────────────────
    async function startAnalysis() {
      if (!canStart.value || isProcessing.value) return

      phase.value = 'chat'
      currentSector.value = selectedSector.value
      isProcessing.value = true

      const question = firstMessage.value.trim() ||
        `Analyse la couverture médiatique — ${currentSectorLabel.value}`
      firstMessage.value = ''

      loadingBlock.value = true
      pendingQuestion.value = question
      await scrollDown()

      const blockIdx = blocks.value.length
      const block = {
        question, summary: null, chartsRendered: false, loadingR: true,
        r1: '', r2: '', streamR1: '', streamR2: '',
        urls: [], suggestions: [], ready: false, streaming: false,
        answer: '', streamAnswer: '',
      }
      blocks.value.push(block)
      loadingBlock.value = false
      block.streaming = true
      await scrollDown()

      // 1. Analyze
      try {
        const res = await fetch(API + '/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: question, sector: currentSector.value }),
        })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()

        block.summary = data.summary
        block.urls = data.top_urls || []
        currentSummary.value = data.summary
        block.chartsRendered = true

        await nextTick()
        renderCharts(blockIdx, data.charts)
        await scrollDown()

      } catch (e) {
        block.r1 = `Erreur : ${e.message}`
        block.loadingR = false
        block.ready = true
        isProcessing.value = false
        return
      }

      // 2. Rapports en parallèle
      const p1 = sse('/report1', { message: question, sector: currentSector.value },
        chunk => { block.streamR1 += chunk; scrollDown() },
        () => { block.r1 = block.streamR1; block.streamR1 = '' }
      )
      const p2 = sse('/report2', { message: question, sector: currentSector.value },
        chunk => { block.streamR2 += chunk; scrollDown() },
        () => { block.r2 = block.streamR2; block.streamR2 = ''; block.loadingR = false }
      )
      await Promise.all([p1, p2])

      // 3. Suggestions
      try {
        const res = await fetch(API + '/suggestions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: question, sector: currentSector.value }),
        })
        const data = await res.json()
        block.suggestions = data.suggestions || []
      } catch {}

      block.ready = true
      block.streaming = false
      isProcessing.value = false
      await scrollDown()
    }

    // ── Follow-up ─────────────────────────────────────────────────────────────
    async function askFollowup(question) {
      question = question?.trim()
      if (!question || isProcessing.value) return

      followupMessage.value = ''
      isProcessing.value = true
      loadingBlock.value = true
      pendingQuestion.value = question

      // Historique des 6 derniers échanges
      const history = blocks.value.slice(-3).flatMap(b => [
        { role: 'user', content: b.question },
        { role: 'assistant', content: (b.r1 || '').slice(0, 300) },
      ])

      await scrollDown()

      const blockIdx = blocks.value.length
      const block = {
        question, summary: null, chartsRendered: false, loadingR: false,
        r1: '', r2: '', streamR1: '', streamR2: '',
        urls: [], suggestions: [], ready: false, streaming: true,
        answer: '', streamAnswer: '',
      }
      blocks.value.push(block)
      loadingBlock.value = false
      await scrollDown()

      await sse('/followup',
        { question, sector: currentSector.value, history },
        async chunk => { block.streamAnswer += chunk; await scrollDown() },
        async () => {
          block.answer = block.streamAnswer
          block.streamAnswer = ''
          block.streaming = false

          // Suggestions après follow-up
          try {
            const res = await fetch(API + '/suggestions', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: question, sector: currentSector.value }),
            })
            const data = await res.json()
            block.suggestions = data.suggestions || []
          } catch {}

          block.ready = true
          isProcessing.value = false
          await scrollDown()
        }
      )
    }

    function reset() {
      phase.value = 'landing'
      blocks.value = []
      firstMessage.value = ''
      followupMessage.value = ''
      isProcessing.value = false
      loadingBlock.value = false
    }

    return {
      phase, selectedSector, firstMessage, followupMessage, canStart,
      sectors, blocks, currentSector, currentSectorLabel,
      isProcessing, loadingBlock, pendingQuestion, streamEl,
      toneClass, goldClass, tensionClass, shortUrl,
      startAnalysis, askFollowup, reset, md,
    }
  }
}).mount('#app')
