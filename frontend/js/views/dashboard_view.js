export const dashboardViewTemplate = `
<section class="panel">
  <h2>闸口总览</h2>
  <p class="hint">过磅票入闸后先封闸写最新闸代快照，无快照禁放行；闸代快照与提单册对账，齐套口径五页同源（就闸口库表）。</p>
  <div class="hero-cards">
    <div class="hero-card"><span class="t">地磅桥</span><div class="n">{{ dash.bridges ?? '—' }}</div></div>
    <div class="hero-card"><span class="t">开放超重</span><div class="n">{{ dash.open_overloads ?? '—' }}</div></div>
    <div class="hero-card"><span class="t">旁路挂起</span><div class="n">{{ dash.side_pending ?? '—' }}</div></div>
    <div class="hero-card"><span class="t">过磅票</span><div class="n">{{ dash.tickets ?? '—' }}</div></div>
    <div class="hero-card"><span class="t">已放行</span><div class="n">{{ dash.gate_releases ?? '—' }}</div></div>
    <div class="hero-card"><span class="t">已封闸</span><div class="n">{{ dash.gate_seals ?? '—' }}</div></div>
    <div class="hero-card"><span class="t">放行缺快照</span><div class="n" :class="(dash.released_missing_snapshot ?? 0) > 0 ? 'bad' : ''">{{ dash.released_missing_snapshot ?? '—' }}</div></div>
  </div>
  <p v-if="(dash.released_missing_snapshot ?? 0) > 0" class="hint recon-warn" style="margin-top:16px">
    无快照禁放警示：存在正式放行缺失最新闸代快照，须回滚补快照，不得判齐套。
  </p>
  <p class="hint" style="margin-top:16px">骨架：{{ dash.meta && dash.meta.skeleton }}</p>
</section>
`;
