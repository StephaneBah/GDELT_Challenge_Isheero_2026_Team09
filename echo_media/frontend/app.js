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
    const selectedSector = ref('libre')   // secteur choisi sur le landing
    // NOTE: currentSector = selectedSector — on utilise selectedSector partout pour éviter la désync
    const firstMessage   = ref('')
    const followupMessage= ref('')
    const isProcessing   = ref(false)
    const loadingBlock   = ref(false)
    const pendingQuestion= ref('')
    const streamEl       = ref(null)

    const pipelineSteps = [
      'Analyse de l\'intention',
      'Filtrage des données GDELT',
      'Construction des visualisations',
      'Rédaction Rapport 1 — Tendances',
      'Rapport 2 — Croisement sources',
    ]
    const currentStep = ref(0)

    // Chaque élément = un échange complet (question + réponse système ou follow-up)
    const blocks = ref([])
    const currentSector = selectedSector   // alias — même ref, zéro désync
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
        id: 'libre', label: 'Libre', desc: 'Tous secteurs',
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

    function renderCharts(blockIdx, chartsData, block) {
      const cfg = { responsive: true, displayModeBar: false }

      console.log(`[renderCharts] blockIdx=${blockIdx}`)
      console.log(`[renderCharts] Plotly disponible:`, typeof Plotly !== 'undefined')
      console.log(`[renderCharts] chartsData keys:`, Object.keys(chartsData || {}))
      console.log(`[renderCharts] tension présent:`, !!chartsData?.tension)
      console.log(`[renderCharts] bubble présent:`,  !!chartsData?.bubble)
      console.log(`[renderCharts] signal présent:`,  !!chartsData?.signal)

      // Premier chart disponible parmi ceux réellement construits
      const firstChartId = ['tension','bubble','signal','partners','themes','actors']
        .find(id => chartsData[id])
      if (!firstChartId) {
        console.warn('[renderCharts] aucun chart dans chartsData, abandon')
        return
      }

      function tryRender(attempt = 0) {
        const el = document.getElementById(`${firstChartId}-${blockIdx}`)
        const w = el ? el.getBoundingClientRect().width : -1

        if (attempt % 5 === 0) {
          console.log(`[tryRender] attempt=${attempt} el=${!!el} width=${w} (cherche ${firstChartId}-${blockIdx})`)
        }

        if (!el || w === 0) {
          if (attempt < 40) {
            requestAnimationFrame(() => tryRender(attempt + 1))
          } else {
            console.error(`[tryRender] ABANDON après 40 tentatives. el=${!!el} width=${w}`)
          }
          return
        }

        console.log(`[tryRender] DOM prêt à attempt=${attempt}, width=${w}px — lancement Plotly`)

        try {
          for (const id of ['tension','bubble','signal','partners','themes','actors']) {
            if (chartsData[id]) {
              const s = JSON.parse(chartsData[id])
              Plotly.newPlot(`${id}-${blockIdx}`, s.data, s.layout, cfg)
              console.log(`[Plotly] ${id} OK`)
            }
          }
          block.chartsRendered = true
          console.log(`[renderCharts] chartsRendered = true`)
        } catch(e) {
          console.error('[Plotly] ERREUR de rendu:', e)
        }
      }

      nextTick(() => {
        console.log(`[renderCharts] nextTick fired, lancement RAF`)
        requestAnimationFrame(() => tryRender())
      })
    }

    // ── Pipeline principal ────────────────────────────────────────────────────
    async function startAnalysis(fromFollowup = false) {
      if (!canStart.value || isProcessing.value) return

      phase.value = 'chat'
      // currentSector === selectedSector (même ref) — pas besoin de copie
      isProcessing.value = true

      const question = firstMessage.value.trim() ||
        `Analyse la couverture médiatique — ${currentSectorLabel.value}`
      firstMessage.value = ''

      currentStep.value = 0
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

      // Étape 0 → 1 : intent en cours, données en cours
      currentStep.value = 0
      await scrollDown()

      // 1. Analyze (intent + filtrage + charts)
      let analyzeData = null
      try {
        currentStep.value = 1   // filtrage données
        const res = await fetch(API + '/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: question, sector: currentSector.value }),
        })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        analyzeData = data
        console.log('[/analyze] réponse reçue:', {
          hasCharts: !!data.charts,
          chartKeys: Object.keys(data.charts || {}),
          tensionLen: data.charts?.tension?.length,
          hasSummary: !!data.summary,
          totalEvents: data.summary?.total_events,
          chartDescription: data.chart_description?.slice(0, 80),
        })

        currentStep.value = 2   // construction visuels
        currentSummary.value = data.summary

        // Toutes les propriétés définies AVANT le push — Vue les rend réactives dès le départ
        block.summary          = data.summary
        block.charts           = data.charts || {}
        block.chartDescription = data.chart_description || ''
        block.anomalyDetail    = data.anomaly_detail || ''
        block.urls             = data.top_urls || []
        block.anomalyUrls      = data.anomaly_urls || []
        block.chartsRendered   = false
        block.streaming        = true   // ← avant push, sinon Vue ne voit pas le changement

        blocks.value.push(block)
        loadingBlock.value = false

        await nextTick()
        renderCharts(blockIdx, data.charts, block)
        await scrollDown()

      } catch (e) {
        block.r1 = `Erreur : ${e.message}`
        block.loadingR = false
        block.ready = true
        block.streaming = false
        loadingBlock.value = false
        blocks.value.push(block)
        isProcessing.value = false
        return
      }

      // 2. Rapports en parallèle — on passe les données déjà calculées
      const intentObj     = analyzeData.intent || {}
      const intentStr     = intentObj.intent_fr || question
      const intentKw      = intentObj.keywords || []
      const chartDesc     = analyzeData.chart_description || ''
      const summaryData   = analyzeData.summary || {}
      const topUrls       = analyzeData.top_urls || []
      const topThemes     = Object.keys(summaryData.top_themes || {})
      const topActors     = Object.keys(summaryData.top_actors || {})

      const r1Body = {
        message: question, sector: currentSector.value,
        chart_description: chartDesc, summary: summaryData,
        intent: intentStr,
      }
      const r2Body = {
        message: question, sector: currentSector.value,
        chart_description: chartDesc, summary: summaryData,
        intent: intentStr, keywords: intentKw, top_urls: topUrls,
        anomaly_detail: block.anomalyDetail || '',
        anomaly_urls: block.anomalyUrls || [],
      }

      currentStep.value = 3   // rapport 1
      let r1Done = false
      const p1 = sse('/report1', r1Body,
        chunk => { block.streamR1 += chunk; scrollDown() },
        () => {
          block.r1 = block.streamR1; block.streamR1 = ''
          r1Done = true; currentStep.value = 4
        }
      )
      currentStep.value = 4   // rapport 2 / sources
      const p2 = sse('/report2', r2Body,
        chunk => { block.streamR2 += chunk; scrollDown() },
        () => { block.r2 = block.streamR2; block.streamR2 = ''; block.loadingR = false }
      )
      await Promise.all([p1, p2])

      // 3. Suggestions — ancrées dans le rapport 1
      try {
        const res = await fetch(API + '/suggestions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: question, sector: currentSector.value,
            report1_text: block.r1,
            intent: intentStr,
            top_themes: topThemes,
            top_actors: topActors,
          }),
        })
        const data2 = await res.json()
        block.suggestions = data2.suggestions || []
      } catch {}

      block.ready = true
      block.streaming = false
      isProcessing.value = false
      await scrollDown()
    }

    // ── Follow-up — routage intelligent ──────────────────────────────────────
    async function askFollowup(question) {
      question = question?.trim()
      if (!question || isProcessing.value) return

      followupMessage.value = ''
      isProcessing.value = true
      loadingBlock.value = true
      pendingQuestion.value = question
      await scrollDown()

      // 1. Routing : est-ce une nouvelle analyse ou une question interprétative ?
      let needsViz = false
      let routeIntent = null
      try {
        const rr = await fetch(API + '/route', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, sector: currentSector.value }),
        })
        const rd = await rr.json()
        needsViz   = rd.needs_viz || false
        routeIntent = rd.intent   || null
        console.log(`[route] needs_viz=${needsViz}`, routeIntent?.intent_fr)
      } catch (e) {
        console.warn('[route] échec routing, fallback conversationnel', e)
      }

      // 2a. Nouvelle analyse → pipeline complet (charts + rapports)
      if (needsViz) {
        loadingBlock.value = false
        // On met à jour le secteur si l'intent pointe vers un autre secteur
        if (routeIntent?.data_focus && routeIntent.data_focus !== 'libre') {
          currentSector.value = routeIntent.data_focus
        }
        // Réutilise startAnalysis avec la question comme firstMessage
        firstMessage.value = question
        await startAnalysis(true)
        return
      }

      // 2b. Question interprétative → réponse conversationnelle
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

      const lastMain   = [...blocks.value].reverse().find(b => b.summary)
      const fuSummary  = lastMain?.summary || currentSummary.value || {}
      const fuChartDesc = lastMain?.chartDescription || ''

      const history = blocks.value.slice(-4).flatMap(b => [
        b.question ? { role: 'user',      content: b.question } : null,
        (b.r1 || b.answer) ? { role: 'assistant', content: (b.r1 || b.answer).slice(0, 300) } : null,
      ]).filter(Boolean)

      await sse('/followup',
        { question, sector: currentSector.value, history, chart_description: fuChartDesc, summary: fuSummary },
        async chunk => { block.streamAnswer += chunk; await scrollDown() },
        async () => {
          block.answer = block.streamAnswer
          block.streamAnswer = ''
          block.streaming = false

          try {
            const res = await fetch(API + '/suggestions', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                message: question, sector: currentSector.value,
                report1_text: block.answer, intent: question,
                top_themes: Object.keys(fuSummary.top_themes || {}),
                top_actors: Object.keys(fuSummary.top_actors || {}),
              }),
            })
            const d = await res.json()
            block.suggestions = d.suggestions || []
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
      selectedSector.value = 'libre'   // remet le secteur à zéro → état landing propre
    }

    return {
      phase, selectedSector, firstMessage, followupMessage, canStart,
      sectors, blocks, currentSector, currentSectorLabel,
      isProcessing, loadingBlock, pendingQuestion, streamEl,
      pipelineSteps, currentStep,
      toneClass, goldClass, tensionClass, shortUrl,
      startAnalysis, askFollowup, reset, md,
    }
  }
}).mount('#app')
